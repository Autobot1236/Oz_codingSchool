from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.db.databases import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)
    phone = Column(String(20), nullable=False)

    medical_records = relationship("MedicalRecord", back_populates="patient")