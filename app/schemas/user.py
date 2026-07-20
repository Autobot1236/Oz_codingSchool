import re

from pydantic import BaseModel, field_validator, EmailStr, Field,
from app.models.enums import Department, Gender, Role

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

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=20)
    name: str = Field(..., max_length=20)
    department: Department
    gender: Gender
    phone_number: str

    @field_validator('password')
    def validate_password_policy(cls, v):
        pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$"
        if not re.match(pattern, v):
            raise ValueError("비밀번호는 8~20자, 대/소문자, 숫자, 특수문자를 포함해야 합니다.")
        return v

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: Role
    is_active: bool

    class Config:
        from_attributes = True
