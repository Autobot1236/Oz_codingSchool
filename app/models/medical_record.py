from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin


class MedicalRecord(TimestampMixin, Base):
    """진료기록(차트). 환자(patients) 1건에 여러 개가 딸릴 수 있다."""

    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chart_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="medical_records")

    # 이 진료기록에 딸린 엑스레이 이미지들 (1:N)
    xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="medical_record",
        cascade="all, delete-orphan",
    )
    # 이 진료기록에 딸린 AI 분석결과들 (1:N) — 여러 모델/재분석 결과가 쌓일 수 있음
    ai_analysis_results: Mapped[list["AiAnalysisResult"]] = relationship(
        back_populates="medical_record",
        cascade="all, delete-orphan",
    )
