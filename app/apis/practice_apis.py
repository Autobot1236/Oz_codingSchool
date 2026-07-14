import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field, field_validator, model_validator


router = APIRouter(prefix="/practice_api", tags=["Practice API"])

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,20}$")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

#임시 회원 데이터
user_list = [
    {
        "id": 1,
        "name": "홍길동",
        "age": 24,
        "email": "gildong24@example.com",
        "password": "Password1234!!",
    },
    {
        "id": 2,
        "name": "장문복",
        "age": 21,
        "email": "moonluck12@example.com",
        "password": "Check1321!",
    },
    {
        "id": 3,
        "name": "임우진",
        "age": 31,
        "email": "limousine33@example.com",
        "password": "lwsPAssword12@",
    },
]


class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str

#회원 생성 요청 모델 
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=10)
    age: int = Field(ge=14)
    email: str = Field(max_length=30)
    password: str = Field(min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        if not EMAIL_PATTERN.match(email):
            raise ValueError("email 형식이 올바르지 않습니다.")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if not PASSWORD_PATTERN.match(password):
            raise ValueError("password는 대문자, 소문자, 특수문자를 각각 1개 이상 포함해야 합니다.")
        return password


#회원 수정 요청 모델
class UserUpdate(BaseModel):
    age: int | None = Field(default=None, ge=14)
    email: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str | None) -> str | None:
        if email is not None and not EMAIL_PATTERN.match(email):
            raise ValueError("email 형식이 올바르지 않습니다.")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str | None) -> str | None:
        if password is not None and not PASSWORD_PATTERN.match(password):
            raise ValueError("password는 대문자, 소문자, 특수문자를 각각 1개 이상 포함해야 합니다.")
        return password

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "UserUpdate":
        if self.age is None and self.email is None and self.password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="수정할 항목을 최소 1개 이상 입력해야 합니다.",
            )
        return self

#Path parameter 검증
UserId = Annotated[int, Path(ge=1, description="회원 ID")]

#다음 ID 계산
def get_next_user_id() -> int:
    if not user_list:
        return 1
    return max(user["id"] for user in user_list) + 1

#회원 찾기 함수 
def find_user(user_id: int) -> dict:
    for user in user_list:
        if user["id"] == user_id:
            return user

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="해당 회원을 찾을 수 없습니다.",
    )

#전체 회원 조회 API
@router.get("/users", response_model=list[UserResponse])
def read_users() -> list[dict]:
    return user_list

#특정 회원 조회 API
@router.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: UserId) -> dict:
    return find_user(user_id)

#회원 생성 API
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate) -> dict:
    new_user = {
        "id": get_next_user_id(),
        "name": user.name,
        "age": user.age,
        "email": user.email,
        "password": user.password,
    }

    user_list.append(new_user)
    return new_user

#회원 수정 API
@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: UserId, user_update: UserUpdate) -> dict:
    user = find_user(user_id)

    update_data = user_update.model_dump(exclude_unset=True)
    user.update(update_data)

    return user

#회원 삭제 API
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UserId) -> None:
    user = find_user(user_id)
    user_list.remove(user)