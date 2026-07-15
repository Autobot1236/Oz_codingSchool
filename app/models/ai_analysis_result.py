from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.db.databases import Base


class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False)
    is_pneumonia = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    ai_model = Column(String(100), nullable=False)

    medical_record = relationship("MedicalRecord", back_populates="ai_analysis_results")