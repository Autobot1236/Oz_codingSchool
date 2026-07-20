import re

from pydantic import BaseModel, field_validator

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("올바른 이메일 형식이어야 합니다.")
        return email


class LoginUserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: LoginUserResponse


class RoleUpdateRequest(BaseModel):
    role: str


class UserRoleResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
