from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, CheckConstraint, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.medical_record import MedicalRecord

class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 100", name="ck_ai_analysis_results_confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(Integer, ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)

    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    heatmap_url: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="ai_analysis_results")
