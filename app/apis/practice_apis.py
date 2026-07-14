# app/apis/practice_apis.py

import re

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

git switch main
git pull origin main
git switch -c feature/practice-list-users

router = APIRouter(
    prefix="/practice_api",
    tags=["practice"],
)


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


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,20}$"
)


def validate_email_value(email: str) -> str:
    if len(email) > 30 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError(
            "올바른 이메일 형식이어야 하며 최대 30자입니다."
        )
    return email


def validate_password_value(password: str) -> str:
    if not PASSWORD_PATTERN.fullmatch(password):
        raise ValueError(
            "비밀번호는 8~20자이며 대문자, 소문자, "
            "특수문자를 포함해야 합니다."
        )
    return password


class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=10)
    age: int = Field(ge=14)
    email: str = Field(max_length=30)
    password: str = Field(min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        return validate_email_value(email)

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_value(password)


class UserUpdate(BaseModel):
    age: int | None = Field(default=None, ge=14)
    email: str | None = Field(default=None, max_length=30)
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=20,
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, email: str | None) -> str | None:
        if email is None:
            return None
        return validate_email_value(email)

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        password: str | None,
    ) -> str | None:
        if password is None:
            return None
        return validate_password_value(password)


def get_user_index(user_id: int) -> int:
    for index, user in enumerate(user_list):
        if user["id"] == user_id:
            return index

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="회원을 찾을 수 없습니다.",
    )


def email_exists(
    email: str,
    excluded_user_id: int | None = None,
) -> bool:
    return any(
        user["email"] == email
        and user["id"] != excluded_user_id
        for user in user_list
    )


# 역할 A 영역
@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="전체 회원 목록 조회",
)
async def list_users() -> list[dict]:
    return user_list


# 역할 B 영역
# 역할 B 담당자가 특정 회원 조회 API를 작성합니다.
@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="특정 회원 조회",
)
async def get_user(user_id: int) -> dict:
    user_index = get_user_index(user_id)
    return user_list[user_index]

# 역할 C 영역
# 역할 C 담당자가 회원 등록 API를 작성합니다.
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원 등록",
)
async def create_user(payload: UserCreate) -> dict:
    if email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다.",
        )

    next_id = max(
        (int(user["id"]) for user in user_list),
        default=0,
    ) + 1

    new_user = {
        "id": next_id,
        **payload.model_dump(),
    }

    user_list.append(new_user)
    return new_user

# 역할 D 영역
# 역할 D 담당자가 회원 수정 API를 작성합니다.
@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="회원 정보 수정",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
) -> dict:
    update_data = payload.model_dump(exclude_none=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 항목을 하나 이상 입력해야 합니다.",
        )

    user_index = get_user_index(user_id)
    current_user = user_list[user_index]

    new_email = update_data.get("email")
    if new_email is not None and email_exists(
        str(new_email),
        excluded_user_id=user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다.",
        )

    current_user.update(update_data)
    return current_user

# 역할 E 영역
# 역할 E 담당자가 회원 삭제 API를 작성합니다.
@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 삭제",
)
async def delete_user(user_id: int) -> Response:
    user_index = get_user_index(user_id)
    user_list.pop(user_index)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
