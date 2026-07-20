from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,20}$")
PHONE_PATTERN = re.compile(r"^\d{10,11}$")


class DepartmentCode(str, Enum):
    MEDICAL = "MEDICAL"
    DEV = "DEV"
    RESEARCH = "RESEARCH"

    @classmethod
    def _missing_(cls, value: object) -> DepartmentCode | None:
        if isinstance(value, str) and value.upper() == "DEVELOPMENT":
            return cls.DEV
        return None


class GenderCode(str, Enum):
    M = "M"
    F = "F"


class UserSignupRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=20)
    name: str = Field(min_length=2, max_length=20)
    department: DepartmentCode
    gender: GenderCode
    phone_number: str = Field(alias="phoneNumber", min_length=10, max_length=11)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: EmailStr) -> str:
        return str(email).lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if not PASSWORD_PATTERN.fullmatch(password):
            raise ValueError(
                "비밀번호는 8~20자이며 대문자, 소문자, 특수문자를 포함해야 합니다."
            )
        return password

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, phone_number: str) -> str:
        if not PHONE_PATTERN.fullmatch(phone_number):
            raise ValueError("휴대폰 번호는 하이픈 없이 10~11자리 숫자여야 합니다.")
        return phone_number


class UserSignupData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    email: str
    name: str
    department: str
    gender: str
    phone_number: str = Field(serialization_alias="phoneNumber")
    role: str
    active: bool
    created_at: datetime = Field(serialization_alias="createdAt")


class UserSignupResponse(BaseModel):
    success: Literal[True] = True
    data: UserSignupData
    message: str = "회원가입이 완료되었습니다."
