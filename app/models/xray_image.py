from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.databases import Base


class XrayImage(Base):
    """엑스레이 이미지. 진료기록(medical_records) 1건에 여러 장이 딸릴 수 있고,
    업로드한 직원(users)도 함께 기록한다.

    주의: ERD에 updated_at 컬럼이 없으므로 TimestampMixin(created_at+updated_at)을
    상속하지 않고 created_at만 직접 선언했다.
    """

    __tablename__ = "xray_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("medical_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploader_id: Mapped[int] = mapped_column(
        Integer,
        # 업로드한 직원이 삭제돼도 이미지 기록은 남아야 하므로 CASCADE를 걸지 않음
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    shooting_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    medical_record: Mapped["MedicalRecord"] = relationship(
        back_populates="xray_images"
    )
    uploader: Mapped["User"] = relationship(back_populates="uploaded_xray_images")
