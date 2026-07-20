import re

from pydantic import BaseModel, Field, field_validator, model_validator


class PasswordChangeRequest(BaseModel):
    currentPassword: str = Field(min_length=1, max_length=128)
    newPassword: str = Field(min_length=8, max_length=64)

    @field_validator("newPassword")
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        if not re.search(r"[A-Za-z]", password):
            raise ValueError("영문을 1자 이상 포함해야 합니다.")
        if not re.search(r"\d", password):
            raise ValueError("숫자를 1자 이상 포함해야 합니다.")
        if not re.search(r"[^A-Za-z0-9]", password):
            raise ValueError("특수문자를 1자 이상 포함해야 합니다.")
        return password

    @model_validator(mode="after")
    def reject_same_password(self) -> "PasswordChangeRequest":
        if self.currentPassword == self.newPassword:
            raise ValueError("새 비밀번호는 기존 비밀번호와 달라야 합니다.")
        return self
