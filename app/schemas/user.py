import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.enums import Department, Gender, Role

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
