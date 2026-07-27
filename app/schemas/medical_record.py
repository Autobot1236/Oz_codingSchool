from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class MedicalRecordListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)


class MedicalRecordCreateResponse(BaseModel):
    id: int
    patient_id: int
    chart_number: str
    symptoms: str
    xray_image_url: str
    shooting_datetime: datetime
    created_at: datetime


class MedicalRecordListItem(BaseModel):
    id: int
    chart_number: str
    symptoms: str
    created_at: datetime


class MedicalRecordListResponse(BaseModel):
    records: list[MedicalRecordListItem]
    page: int
    size: int
    total: int


class MedicalRecordDetailResponse(BaseModel):
    data: MedicalRecordDetailData


class PredictionListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)


class PredictionItem(BaseModel):
    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float = Field(ge=0.0, le=100.0)
    heatmap_url: str | None
    ai_model: str = Field(min_length=1, max_length=50)
    created_at: datetime


class PredictionResponse(PredictionItem):
    cached: bool


class PredictionListResponse(BaseModel):
    predictions: list[PredictionItem]
    page: int
    size: int
    total: int
