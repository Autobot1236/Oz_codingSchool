from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class AiAnalysisResult(TimestampMixin, Base):
    """AI 폐렴 분석 결과. 진료기록(medical_records) 1건에 여러 건이 딸릴 수 있다
    (여러 모델로 분석하거나 재분석하는 경우)."""

    __tablename__ = "ai_analysis_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("medical_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_pneumonia: Mapped[bool] = mapped_column(Boolean, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    heatmap_url: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(50), nullable=False)

    medical_record: Mapped["MedicalRecord"] = relationship(
        back_populates="ai_analysis_results"
    )
