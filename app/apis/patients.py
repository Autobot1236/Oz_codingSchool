from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.enums import Role
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientDetailData, PatientDetailResponse

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


def ensure_staff_or_admin(current_user: User) -> None:
    if current_user.role not in {Role.STAFF, Role.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="환자 정보에 접근할 권한이 없습니다.",
        )


@router.get(
    "/{patient_id}",
    response_model=PatientDetailResponse,
    summary="환자 상세 조회",
)
async def get_patient_detail(
    patient_id: int,
    session: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
) -> PatientDetailResponse:
    ensure_staff_or_admin(current_user)

    result = await session.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
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

