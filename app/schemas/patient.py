import re
from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import Gender


def normalize_patient_name(name: str) -> str:
    normalized_name = name.strip()
    if not 1 <= len(normalized_name) <= 30:
        raise ValueError("name은 공백 제거 후 1자 이상 30자 이하여야 합니다.")
    return normalized_name


def normalize_phone_number(phone_number: str) -> str:
    normalized_phone_number = phone_number.strip()
    if re.fullmatch(r"\d{10,11}", normalized_phone_number) is None:
        raise ValueError("phone_number는 하이픈 없는 숫자 10~11자리여야 합니다.")
    return normalized_phone_number


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    age: int = Field(ge=0, le=150)
    gender: Gender
    phone_number: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        return normalize_patient_name(name)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, phone_number: str) -> str:
        return normalize_phone_number(phone_number)


class PatientUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    phone_number: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        return normalize_patient_name(name)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, phone_number: str | None) -> str | None:
        if phone_number is None:
            return None
        return normalize_phone_number(phone_number)

    @model_validator(mode="after")
    def reject_explicit_null(self) -> Self:
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name}에는 null을 사용할 수 없습니다.")
        return self


class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: Gender
    phone_number: str
    created_at: datetime
    updated_at: datetime | None


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
