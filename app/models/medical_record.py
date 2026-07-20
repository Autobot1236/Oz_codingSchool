from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ai_analysis_result import AIAnalysisResult
    from app.models.patient import Patient
    from app.models.xray_image import XrayImage

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    chart_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    xray_images: Mapped[List["XrayImage"]] = relationship(back_populates="medical_record", cascade="all, delete-orphan")
    ai_analysis_results: Mapped[List["AIAnalysisResult"]] = relationship(back_populates="medical_record", cascade="all, delete-orphan")
