from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import Gender


class PatientDetailData(BaseModel):
    id: int
    name: str
    age: int
    gender: Gender | None
    phone_number: str
    created_at: datetime
    updated_at: datetime | None


class PatientDetailResponse(BaseModel):
    data: PatientDetailData

