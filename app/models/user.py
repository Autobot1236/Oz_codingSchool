import enum

from sqlalchemy import Boolean, Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.core.db.databases import Base


class UserRole(str, enum.Enum):
    pending = "pending"
    staff = "staff"
    admin = "admin"


class Department(str, enum.Enum):
    research = "research"
    medical = "medical"
    development = "development"


class Gender(str, enum.Enum):
    male = "M"
    female = "F"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    phone_number = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    department = Column(Enum(Department), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.pending)
    is_active = Column(Boolean, nullable=False, default=True)

    xray_images = relationship("XrayImage", back_populates="uploader", cascade="all, delete-orphan")
