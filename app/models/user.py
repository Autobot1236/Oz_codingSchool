import enum

from sqlalchemy import Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.core.db.databases import Base


class UserRole(str, enum.Enum):
    doctor = "doctor"
    nurse = "nurse"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    role = Column(Enum(UserRole), nullable=False)

    xray_images = relationship("XrayImage", back_populates="uploader")