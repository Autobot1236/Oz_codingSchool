from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import Gender


class PatientListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=30)
    gender: Gender | None = None
    min_age: int | None = Field(default=None, ge=0, le=150)
    max_age: int | None = Field(default=None, ge=0, le=150)
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        normalized_name = name.strip()
        return normalized_name or None

    @model_validator(mode="after")
    def validate_age_range(self) -> Self:
        if (
            self.min_age is not None
            and self.max_age is not None
            and self.min_age > self.max_age
        ):
            raise ValueError("min_age는 max_age보다 클 수 없습니다.")
        return self


class PatientListItem(BaseModel):
    id: int
    name: str
    age: int
    gender: Gender
    phone_number: str
    created_at: datetime
    updated_at: datetime | None


class PatientListResponse(BaseModel):
    patients: list[PatientListItem]
    page: int
    size: int
    total: int
