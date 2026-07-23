import logging
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Department
from app.models.patient import Patient
from app.models.user import User
from app.repositories import patient_repository
from app.schemas.patient import (
    PatientCreate,
    PatientDetailData,
    PatientDetailResponse,
    PatientListItem,
    PatientListQuery,
    PatientListResponse,
    PatientResponse,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
XRAY_MEDIA_ROOT = (PROJECT_ROOT / "media" / "xray").resolve()


def require_medical_department(current_user: User) -> None:
    if current_user.department != Department.MEDICAL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="medical_department_required",
        )


def to_patient_response(patient: Patient) -> PatientResponse:
    return PatientResponse(
        id=patient.id,
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        phone_number=patient.phone,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


async def create_patient(
    session: AsyncSession,
    payload: PatientCreate,
    current_user: User,
) -> PatientResponse:
    require_medical_department(current_user)

    patient = Patient(
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        phone=payload.phone_number,
    )

    patient_repository.add_patient(session, patient)

    try:
        await session.commit()
        await session.refresh(patient)
    except Exception:
        await session.rollback()
        raise

    return to_patient_response(patient)


async def list_patients(
    session: AsyncSession,
    query: PatientListQuery,
) -> PatientListResponse:
    patients, total = await patient_repository.list_patients(
        session,
        name=query.name,
        gender=query.gender,
        min_age=query.min_age,
        max_age=query.max_age,
        page=query.page,
        size=query.size,
    )

    return PatientListResponse(
        patients=[
            PatientListItem(
                id=patient.id,
                name=patient.name,
                age=patient.age,
                gender=patient.gender,
                phone_number=patient.phone,
                created_at=patient.created_at,
                updated_at=patient.updated_at,
            )
            for patient in patients
        ],
        page=query.page,
        size=query.size,
        total=total,
    )


async def get_patient_detail(
    session: AsyncSession,
    patient_id: int,
) -> PatientDetailResponse:
    patient = await patient_repository.get_patient_by_id(
        session,
        patient_id,
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="환자 정보를 찾을 수 없습니다.",
        )

    return PatientDetailResponse(
        data=PatientDetailData(
            id=patient.id,
            name=patient.name,
            age=patient.age,
            gender=patient.gender,
            phone_number=patient.phone,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
        )
    )


async def delete_patient(
    session: AsyncSession,
    patient_id: int,
    current_user: User,
) -> None:
    require_medical_department(current_user)

    patient = await patient_repository.get_patient_by_id(
        session,
        patient_id,
    )

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="patient_not_found",
        )

    xray_image_urls = (
        await patient_repository.list_patient_xray_image_urls(
            session,
            patient_id,
        )
    )

    await patient_repository.delete_patient(session, patient)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    for image_url in xray_image_urls:
        delete_xray_file_safely(image_url)


def delete_xray_file_safely(image_url: str) -> None:
    relative_path = image_url.lstrip("/")

    if relative_path.startswith("media/xray/"):
        relative_path = relative_path.removeprefix(
            "media/xray/"
        )

    candidate_path = (
        XRAY_MEDIA_ROOT / relative_path
    ).resolve()

    try:
        candidate_path.relative_to(XRAY_MEDIA_ROOT)
    except ValueError:
        logger.warning(
            "X-Ray 파일 삭제를 건너뜁니다. "
            "허용된 경로 밖입니다: %s",
            image_url,
        )
        return

    try:
        candidate_path.unlink(missing_ok=True)
    except OSError:
        logger.exception(
            "환자 DB 삭제 후 X-Ray 파일 삭제에 실패했습니다: %s",
            candidate_path,
        )