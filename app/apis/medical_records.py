from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.enums import Role
from app.models.user import User
from app.schemas.medical_record import (
    MedicalRecordCreateResponse,
    MedicalRecordDetailResponse,
    MedicalRecordListQuery,
    MedicalRecordListResponse,
)
from app.services import medical_record_service

router = APIRouter(prefix="/api/v1", tags=["medical-records"])


def ensure_staff_or_admin(current_user: User) -> None:
    if current_user.role not in {Role.STAFF, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="진료기록에 접근할 권한이 없습니다.",
        )


@router.post(
    "/patients/{patient_id}/medical-records",
    response_model=MedicalRecordCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="진료기록 등록",
)
async def create_medical_record(
    patient_id: int,
    chart_number: Annotated[str, Form(min_length=1, max_length=50)],
    symptoms: Annotated[str, Form(min_length=1)],
    xray_image: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> MedicalRecordCreateResponse:
    return await medical_record_service.create_medical_record(
        session=session,
        patient_id=patient_id,
        chart_number=chart_number,
        symptoms=symptoms,
        xray_image=xray_image,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/medical-records",
    response_model=MedicalRecordListResponse,
    summary="환자별 진료기록 목록 조회",
)
async def list_medical_records(
    patient_id: int,
    query: Annotated[MedicalRecordListQuery, Query()],
    _current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> MedicalRecordListResponse:
    return await medical_record_service.list_medical_records(
        session=session,
        patient_id=patient_id,
        query=query,
    )


@router.get(
    "/medical-records/{record_id}",
    response_model=MedicalRecordDetailResponse,
    summary="진료기록 상세 조회",
)
async def get_medical_record_detail(
    record_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> MedicalRecordDetailResponse:
    ensure_staff_or_admin(current_user)
    return await medical_record_service.get_medical_record_detail(
        session=session,
        record_id=record_id,
    )
