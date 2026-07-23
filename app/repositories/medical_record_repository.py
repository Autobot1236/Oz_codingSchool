from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_record import MedicalRecord
from app.models.xray_image import XrayImage


async def get_medical_record_by_chart_number(
    session: AsyncSession,
    chart_number: str,
) -> MedicalRecord | None:
    result = await session.execute(
        select(MedicalRecord).where(
            MedicalRecord.chart_number == chart_number
        )
    )
    return result.scalar_one_or_none()


def add_medical_record(
    session: AsyncSession,
    medical_record: MedicalRecord,
) -> None:
    session.add(medical_record)


def add_xray_image(
    session: AsyncSession,
    xray_image: XrayImage,
) -> None:
    session.add(xray_image)


async def list_medical_records(
    session: AsyncSession,
    patient_id: int,
    page: int,
    size: int,
) -> tuple[list[MedicalRecord], int]:
    records_result = await session.execute(
        select(MedicalRecord)
        .where(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.created_at.desc(), MedicalRecord.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    total_result = await session.execute(
        select(func.count(MedicalRecord.id)).where(
            MedicalRecord.patient_id == patient_id
        )
    )
    return (
        list(records_result.scalars().all()),
        total_result.scalar_one(),
    )


async def get_medical_record_by_id(
    session: AsyncSession,
    record_id: int,
) -> MedicalRecord | None:
    result = await session.execute(
        select(MedicalRecord)
        .options(selectinload(MedicalRecord.xray_images))
        .where(MedicalRecord.id == record_id)
    )
    return result.scalar_one_or_none()
