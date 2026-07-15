from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.db.databases import Base


class XrayImage(Base):
    __tablename__ = "xray_images"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    shooting_datetime = Column(DateTime, nullable=False)

    medical_record = relationship("MedicalRecord", back_populates="xray_images")
    uploader = relationship("User", back_populates="xray_images")