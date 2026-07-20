from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Integer, Boolean, DateTime, Enum as SQLEnum, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, GenderEnum, DepartmentEnum, RoleEnum

if TYPE_CHECKING:
    from app.models.xray_image import XrayImage

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(20))
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True)

    # SQLite3 호환을 위해 native_enum=False 설정
    gender: Mapped[GenderEnum] = mapped_column(SQLEnum(GenderEnum, native_enum=False, create_constraint=True), nullable=False)
    department: Mapped[DepartmentEnum] = mapped_column(SQLEnum(DepartmentEnum, native_enum=False, create_constraint=True), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SQLEnum(RoleEnum, native_enum=False, create_constraint=True), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    uploaded_xrays: Mapped[List["XrayImage"]] = relationship(back_populates="uploader")
