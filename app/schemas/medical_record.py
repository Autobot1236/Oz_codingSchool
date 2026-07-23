from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class XrayImageResponse(BaseModel):
    id: int
    image_url: str
    shooting_datetime: datetime
    created_at: datetime


class MedicalRecordDetailData(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_images: list[XrayImageResponse]
    created_at: datetime
    updated_at: datetime | None


class MedicalRecordDetailResponse(BaseModel):
    data: MedicalRecordDetailData

