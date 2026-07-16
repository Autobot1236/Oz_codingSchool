from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base

if TYPE_CHECKING:
    from app.models.ai_analysis_result import AIAnalysisResult
    from app.models.patient import Patient
    from app.models.xray_image import XrayImage


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    chart_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=datetime.utcnow, nullable=True
    )

    patient: Mapped[Patient] = relationship(back_populates="medical_records")
    xray_images: Mapped[list[XrayImage]] = relationship(
        back_populates="medical_record", cascade="all, delete-orphan", passive_deletes=True
    )
    ai_analysis_results: Mapped[list[AIAnalysisResult]] = relationship(
        back_populates="medical_record", cascade="all, delete-orphan", passive_deletes=True
    )
