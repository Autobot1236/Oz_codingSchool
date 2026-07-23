from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories import patient_repository
from app.schemas.patient import (
    PatientDetailData,
    PatientDetailResponse,
    PatientListItem,
    PatientListQuery,
    PatientListResponse,
)


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
    patient = await patient_repository.get_patient_by_id(session, patient_id)
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
