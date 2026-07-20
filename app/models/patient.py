from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.models.enums import Gender

if TYPE_CHECKING:
    from app.models.medical_record import MedicalRecord


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender), nullable=True)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )

    medical_records: Mapped[list[MedicalRecord]] = relationship(
        back_populates="patient", cascade="all, delete-orphan", passive_deletes=True
    )
