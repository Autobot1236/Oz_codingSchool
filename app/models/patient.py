from sqlalchemy import Enum, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base
from app.core.db.models import TimestampMixin
from app.models.enums import GenderEnum


class Patient(TimestampMixin, Base):
    """환자. users(직원 계정)와는 별개의 테이블 — 환자는 로그인하지 않는다."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # ERD상 gender는 NN(필수) 표시가 없어 선택값으로 둠 — 실제 정책에 맞게 nullable 조정
    gender: Mapped[GenderEnum | None] = mapped_column(Enum(GenderEnum), nullable=True)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)

    # 이 환자의 진료기록들 (1:N) — 환자가 삭제되면 진료기록도 함께 삭제
    medical_records: Mapped[list["MedicalRecord"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
    )
