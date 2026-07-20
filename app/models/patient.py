from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, String, Integer, SmallInteger, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, GenderEnum

if TYPE_CHECKING:
    from app.models.medical_record import MedicalRecord

class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (CheckConstraint("age >= 0", name="ck_patients_age_non_negative"),)

    # SQLite3의 BigInteger 자동증가는 Integer primary key와 동일하게 작동하므로 Integer로 통일합니다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[Optional[GenderEnum]] = mapped_column(SQLEnum(GenderEnum, native_enum=False, create_constraint=True), nullable=True)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    medical_records: Mapped[List["MedicalRecord"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
