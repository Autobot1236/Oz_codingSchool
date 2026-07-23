from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Gender
from app.models.patient import Patient


async def list_patients(
    session: AsyncSession,
    *,
    name: str | None,
    gender: Gender | None,
    min_age: int | None,
    max_age: int | None,
    page: int,
    size: int,
) -> tuple[list[Patient], int]:
    conditions = []
    if name is not None:
        conditions.append(Patient.name.contains(name, autoescape=True))
    if gender is not None:
        conditions.append(Patient.gender == gender)
    if min_age is not None:
        conditions.append(Patient.age >= min_age)
    if max_age is not None:
        conditions.append(Patient.age <= max_age)

    patients_result = await session.execute(
        select(Patient)
        .where(*conditions)
        .order_by(Patient.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    total_result = await session.execute(
        select(func.count(Patient.id)).where(*conditions)
    )

    return list(patients_result.scalars().all()), total_result.scalar_one()


async def get_patient_by_id(
    session: AsyncSession,
    patient_id: int,
) -> Patient | None:
    result = await session.execute(select(Patient).where(Patient.id == patient_id))
    return result.scalar_one_or_none()
