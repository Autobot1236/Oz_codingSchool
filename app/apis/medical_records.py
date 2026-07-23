from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.enums import Role
from app.models.medical_record import MedicalRecord
from app.models.user import User
from app.schemas.medical_record import (
    MedicalRecordDetailData,
    MedicalRecordDetailResponse,
    XrayImageResponse,
)

router = APIRouter(prefix="/api/v1/medical-records", tags=["medical-records"])


def ensure_staff_or_admin(current_user: User) -> None:
    if current_user.role not in {Role.STAFF, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="진료기록에 접근할 권한이 없습니다.",
        )


@router.get(
    "/{record_id}",
    response_model=MedicalRecordDetailResponse,
    summary="진료기록 상세 조회",
)
async def get_medical_record_detail(
    record_id: int,
    session: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
) -> MedicalRecordDetailResponse:
    ensure_staff_or_admin(current_user)

    result = await session.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(MedicalRecord.id == record_id)
    )
    medical_record = result.scalar_one_or_none()
    if medical_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="진료기록을 찾을 수 없습니다.",
        )

    return MedicalRecordDetailResponse(
        data=MedicalRecordDetailData(
            id=medical_record.id,
            patient_id=medical_record.patient_id,
            chart_number=medical_record.chart_number,
            symptoms=medical_record.symptoms,
            xray_images=[
                XrayImageResponse(
                    id=xray_image.id,
                    image_url=xray_image.image_url,
                    shooting_datetime=xray_image.shooting_datetime,
                    created_at=xray_image.created_at,
                )
                for xray_image in medical_record.xray_images
            ],
            created_at=medical_record.created_at,
            updated_at=medical_record.updated_at,
        )
    )

