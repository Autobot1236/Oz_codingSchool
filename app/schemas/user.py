import re

from pydantic import BaseModel, field_validator, EmailStr, Field, model_validator, , ConfigDict
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


class UserProfileResponse(BaseModel):
    name: str
    email: str
    department: str
    gender: str
    phone_number: str
    role: str


class UserProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: str | None = None
    phone_number: str | None = None

    @field_validator("department")
    @classmethod
    def validate_department(cls, department: str | None) -> str:
        if department is None:
            raise ValueError("department에는 null을 입력할 수 없습니다.")
        return department

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, phone_number: str | None) -> str:
        if phone_number is None:
            raise ValueError("phone_number에는 null을 입력할 수 없습니다.")
        if not re.fullmatch(r"\d{10,11}", phone_number):
            raise ValueError("휴대폰 번호는 숫자 10~11자리여야 합니다.")
        return phone_number

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