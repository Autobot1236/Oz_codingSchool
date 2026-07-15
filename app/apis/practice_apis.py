from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
import re
 
router = APIRouter(
    prefix="/practice_api",
    tags=["Practice API"],
)
 
# ── 데이터 ──
user_list = [
    {"id": 1, "name": "홍길동", "age": 24, "email": "gildong24@example.com",   "password": "Password1234!!"},
    {"id": 2, "name": "장문복", "age": 21, "email": "moonluck12@example.com",  "password": "Check1321!"},
    {"id": 3, "name": "임우진", "age": 31, "email": "limousine33@example.com", "password": "lwsPAssword12@"},
]
 
# ── 유효성 검사 정규표현식 ──
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
PW_REGEX    = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};\'\\:"|,.<>\/?]).{8,20}$')
 
def validate_email_format(email: str) -> str:
    if len(email) > 30:
        raise ValueError("이메일은 최대 30자까지 입력 가능합니다.")
    if not EMAIL_REGEX.match(email):
        raise ValueError("올바른 이메일 형식이 아닙니다.")
    return email
 
def validate_password_format(password: str) -> str:
    if not PW_REGEX.match(password):
        raise ValueError("비밀번호는 대문자, 소문자, 특수문자를 각 1개 이상 포함하고 8~20자여야 합니다.")
    return password
 
# ── 스키마 ──
class UserCreate(BaseModel):
    name:     str
    age:      int
    email:    str
    password: str
 
    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not (2 <= len(v) <= 10):
            raise ValueError("이름은 최소 2글자, 최대 10글자여야 합니다.")
        return v
 
    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v < 14:
            raise ValueError("나이는 최소 14세 이상이어야 합니다.")
        return v
 
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return validate_email_format(v)
 
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return validate_password_format(v)
 
 
class UserUpdate(BaseModel):
    age:      Optional[int] = None
    email:    Optional[str] = None
    password: Optional[str] = None
 
    @model_validator(mode="after")
    def check_at_least_one(self):
        if self.age is None and self.email is None and self.password is None:
            raise ValueError("age, email, password 중 하나 이상 입력해야 합니다.")
        return self
 
    @field_validator("age")
    @classmethod
    def validate_age(cls, v):
        if v is not None and v < 14:
            raise ValueError("나이는 최소 14세 이상이어야 합니다.")
        return v
 
    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v is not None:
            return validate_email_format(v)
        return v
 
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v is not None:
            return validate_password_format(v)
        return v
 
 
# ── 헬퍼 ──
def find_user(user_id: int):
    for user in user_list:
        if user["id"] == user_id:
            return user
    return None
 
 
# ── 1. 전체 회원 목록 조회 GET ──
@router.get("/users")
def get_users():
    return [
        {"id": u["id"], "name": u["name"], "age": u["age"], "email": u["email"]}
        for u in user_list
    ]
 
 
# ── 2. 특정 회원 조회 GET ──
@router.get("/users/{user_id}")
def get_user(user_id: int = Path(..., description="조회할 회원 ID")):
    user = find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="해당 ID의 회원을 찾을 수 없습니다.")
    return {"id": user["id"], "name": user["name"], "age": user["age"], "email": user["email"]}
 
 
# ── 3. 회원 추가 POST ──
@router.post("/users", status_code=201)
def create_user(body: UserCreate):
    for u in user_list:
        if u["email"] == body.email:
            raise HTTPException(status_code=400, detail="이미 사용 중인 이메일입니다.")
 
    new_id = max(u["id"] for u in user_list) + 1 if user_list else 1
    new_user = {
        "id":       new_id,
        "name":     body.name,
        "age":      body.age,
        "email":    body.email,
        "password": body.password,
    }
    user_list.append(new_user)
    return {"message": "회원이 추가되었습니다.", "id": new_id}
 
 
# ── 4. 회원 수정 PATCH ──
@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate):
    user = find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="해당 ID의 회원을 찾을 수 없습니다.")
 
    if body.age is not None:
        user["age"] = body.age
    if body.email is not None:
        user["email"] = body.email
    if body.password is not None:
        user["password"] = body.password
 
    return {"message": "회원 정보가 수정되었습니다.", "id": user_id}
 
 
# ── 5. 회원 삭제 DELETE ──
@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    user = find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="해당 ID의 회원을 찾을 수 없습니다.")
 
    user_list.remove(user)
    return {"message": "회원이 삭제되었습니다.", "id": user_id}