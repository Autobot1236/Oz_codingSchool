from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import patient_repository
from app.schemas.patient import (
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
