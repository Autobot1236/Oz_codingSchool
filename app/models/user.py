from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.models.enums import DepartmentEnum, GenderEnum, RoleEnum


class User(TimestampMixin, Base):
    """직원 계정 (의료진 / 개발팀 / 연구진). 환자(Patient)와는 별도의 로그인 계정 테이블."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    gender: Mapped[GenderEnum] = mapped_column(Enum(GenderEnum), nullable=False)
    department: Mapped[DepartmentEnum] = mapped_column(
        Enum(DepartmentEnum), nullable=False
    )
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum), nullable=False, default=RoleEnum.PENDING
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 이 직원이 업로드한 엑스레이 이미지들 (1:N)
    uploaded_xray_images: Mapped[list["XrayImage"]] = relationship(
        back_populates="uploader"
    )
