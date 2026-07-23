from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Department
from app.models.medical_record import MedicalRecord
from app.models.user import User
from app.models.xray_image import XrayImage
from app.repositories import medical_record_repository, patient_repository
from app.schemas.medical_record import (
    MedicalRecordCreateResponse,
    MedicalRecordDetailResponse,
    MedicalRecordListItem,
    MedicalRecordListQuery,
    MedicalRecordListResponse,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
XRAY_MEDIA_ROOT = (PROJECT_ROOT / "media" / "xray").resolve()
MAX_XRAY_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_XRAY_CONTENT_TYPES = {"image/jpeg", "image/png"}
JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def require_medical_department(current_user: User) -> None:
    if current_user.department != Department.MEDICAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="medical_department_required",
        )


def normalize_chart_number(chart_number: str) -> str:
    normalized_chart_number = chart_number.strip()
    if not 1 <= len(normalized_chart_number) <= 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_chart_number",
        )
    return normalized_chart_number


def normalize_symptoms(symptoms: str) -> str:
    normalized_symptoms = symptoms.strip()
    if not normalized_symptoms:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_symptoms",
        )
    return normalized_symptoms


async def validate_xray_image(xray_image: UploadFile) -> tuple[bytes, str]:
    try:
        image_content = await xray_image.read(MAX_XRAY_FILE_SIZE + 1)
    finally:
        await xray_image.close()

    if (
        xray_image.content_type not in ALLOWED_XRAY_CONTENT_TYPES
        or not image_content
        or len(image_content) > MAX_XRAY_FILE_SIZE
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invalid_xray_image",
        )

    if (
        xray_image.content_type == "image/jpeg"
        and image_content.startswith(JPEG_SIGNATURE)
    ):
        return image_content, ".jpg"
    if (
        xray_image.content_type == "image/png"
        and image_content.startswith(PNG_SIGNATURE)
    ):
        return image_content, ".png"

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="invalid_xray_image",
    )


async def create_medical_record(
    session: AsyncSession,
    patient_id: int,
    chart_number: str,
    symptoms: str,
    xray_image: UploadFile,
    current_user: User,
) -> MedicalRecordCreateResponse:
    require_medical_department(current_user)
    normalized_chart_number = normalize_chart_number(chart_number)
    normalized_symptoms = normalize_symptoms(symptoms)

    patient = await patient_repository.get_patient_by_id(session, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient_not_found",
        )

    existing_record = (
        await medical_record_repository.get_medical_record_by_chart_number(
            session,
            normalized_chart_number,
        )
    )
    if existing_record is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="chart_number_already_exists",
        )

    image_content, extension = await validate_xray_image(xray_image)
    filename = f"{uuid4().hex}{extension}"
    image_path = (XRAY_MEDIA_ROOT / filename).resolve()
    image_url = f"/media/xray/{filename}"
    shooting_datetime = datetime.now(timezone.utc).replace(tzinfo=None)

    await run_in_threadpool(XRAY_MEDIA_ROOT.mkdir, parents=True, exist_ok=True)
    await run_in_threadpool(image_path.write_bytes, image_content)

    medical_record = MedicalRecord(
        patient_id=patient_id,
        chart_number=normalized_chart_number,
        symptoms=normalized_symptoms,
    )
    medical_record_repository.add_medical_record(session, medical_record)

    try:
        await session.flush()
        saved_xray_image = XrayImage(
            record_id=medical_record.id,
            uploader_id=current_user.id,
            image_url=image_url,
            shooting_datetime=shooting_datetime,
        )
        medical_record_repository.add_xray_image(session, saved_xray_image)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        await run_in_threadpool(image_path.unlink, missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="chart_number_already_exists",
        ) from exc
    except Exception:
        await session.rollback()
        await run_in_threadpool(image_path.unlink, missing_ok=True)
        raise

    await session.refresh(medical_record)
    await session.refresh(saved_xray_image)
    return MedicalRecordCreateResponse(
        id=medical_record.id,
        patient_id=medical_record.patient_id,
        chart_number=medical_record.chart_number,
        symptoms=medical_record.symptoms,
        xray_image_url=saved_xray_image.image_url,
        shooting_datetime=saved_xray_image.shooting_datetime,
        created_at=medical_record.created_at,
    )


async def list_medical_records(
    session: AsyncSession,
    patient_id: int,
    query: MedicalRecordListQuery,
) -> MedicalRecordListResponse:
    patient = await patient_repository.get_patient_by_id(session, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient_not_found",
        )

    medical_records, total = (
        await medical_record_repository.list_medical_records(
            session,
            patient_id,
            query.page,
            query.size,
        )
    )
    return MedicalRecordListResponse(
        records=[
            MedicalRecordListItem(
                id=medical_record.id,
                chart_number=medical_record.chart_number,
                symptoms=(
                    medical_record.symptoms
                    if len(medical_record.symptoms) <= 100
                    else f"{medical_record.symptoms[:100]}…"
                ),
                created_at=medical_record.created_at,
            )
            for medical_record in medical_records
        ],
        page=query.page,
        size=query.size,
        total=total,
    )


async def get_medical_record_detail(
    session: AsyncSession,
    record_id: int,
) -> MedicalRecordDetailResponse:
    medical_record = (
        await medical_record_repository.get_medical_record_by_id(
            session,
            record_id,
        )
    )
    if medical_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="medical_record_not_found",
        )

    xray_image = medical_record.xray_images[0]
    return MedicalRecordDetailResponse(
        id=medical_record.id,
        patient_id=medical_record.patient_id,
        chart_number=medical_record.chart_number,
        symptoms=medical_record.symptoms,
        xray_image_url=xray_image.image_url,
        shooting_datetime=xray_image.shooting_datetime,
        created_at=medical_record.created_at,
    )
