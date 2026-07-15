from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db.databases import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    chart_number = Column(String(50), unique=True, nullable=False, index=True)
    symptoms = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="medical_records")
    xray_images = relationship("XrayImage", back_populates="medical_record")
    ai_analysis_results = relationship("AIAnalysisResult", back_populates="medical_record")