import re
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.user import Department, Gender, User, UserRole

router = APIRouter(prefix="/api/v1", tags=["users"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
DbSession = Annotated[AsyncSession, Depends(async_get_db)]

PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$")
PHONE_PATTERN = re.compile(r"^01[016789]-?\d{3,4}-?\d{4}$")


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


class SignupRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=50)
    department: Department
    gender: Gender
    phone_number: str = Field(max_length=20)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if not re.fullmatch(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value):
            raise ValueError("유효한 이메일 형식이 아닙니다.")
        return value.lower()

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.fullmatch(value):
            raise ValueError("비밀번호는 영문 대소문자, 숫자, 특수문자를 포함해야 합니다.")
        return value

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("유효한 휴대폰 번호 형식이 아닙니다.")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    department: Department
    gender: Gender
    phone_number: str
    role: UserRole
    is_active: bool


class MyProfileUpdate(BaseModel):
    department: Department | None = None
    phone_number: str | None = Field(default=None, max_length=20)

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, value: str | None) -> str | None:
        if value is not None and not PHONE_PATTERN.fullmatch(value):
            raise ValueError("유효한 휴대폰 번호 형식이 아닙니다.")
        return value


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if not PASSWORD_PATTERN.fullmatch(value):
            raise ValueError("비밀번호는 영문 대소문자, 숫자, 특수문자를 포함해야 합니다.")
        return value


class RoleUpdateRequest(BaseModel):
    user_id: int
    new_role: UserRole


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    try:
        user_id = decode_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="인증 토큰이 유효하지 않습니다.", headers={"WWW-Authenticate": "Bearer"})
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="인증된 사용자가 아닙니다.")
    return user


async def get_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role is not UserRole.admin:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current_user


def access_token(user_id: int) -> str:
    return create_token(user_id, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def refresh_token(user_id: int) -> str:
    return create_token(user_id, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie("refresh_token", token, max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, httponly=True, secure=settings.COOKIE_SECURE, samesite="lax", path="/api/v1/users")


@router.post("/users/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, db: DbSession) -> User:
    user = User(email=payload.email, name=payload.name, department=payload.department, gender=payload.gender, phone_number=payload.phone_number, password_hash=hash_password(payload.password), role=UserRole.pending)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("이미 사용 중인 이메일 또는 휴대폰 번호입니다.")
    await db.refresh(user)
    return user


@router.post("/users/login")
async def login(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> dict[str, str]:
    user = await db.scalar(select(User).where(User.email == form_data.username))
    if not user or not user.is_active or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    set_refresh_cookie(response, refresh_token(user.id))
    return {"access_token": access_token(user.id), "token_type": "bearer"}


@router.post("/users/refresh")
async def refresh(response: Response, db: DbSession, refresh_token_value: Annotated[str | None, Cookie(alias="refresh_token")] = None) -> dict[str, str]:
    if not refresh_token_value:
        raise HTTPException(status_code=401, detail="리프레시 토큰이 없습니다.")
    try:
        user_id = decode_token(refresh_token_value)
    except ValueError:
        response.delete_cookie("refresh_token", path="/api/v1/users")
        raise HTTPException(status_code=401, detail="리프레시 토큰이 만료되었거나 유효하지 않습니다.")
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="인증된 사용자가 아닙니다.")
    set_refresh_cookie(response, refresh_token(user.id))
    return {"access_token": access_token(user.id), "token_type": "bearer"}


@router.post("/users/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, _: Annotated[User, Depends(get_current_user)]) -> Response:
    response.delete_cookie("refresh_token", path="/api/v1/users")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/users/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.patch("/users/me", response_model=UserResponse)
async def update_me(payload: MyProfileUpdate, db: DbSession, current_user: Annotated[User, Depends(get_current_user)]) -> User:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="수정할 항목을 입력하세요.")
    for field, value in changes.items():
        setattr(current_user, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("이미 사용 중인 휴대폰 번호입니다.")
    await db.refresh(current_user)
    return current_user


@router.patch("/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(payload: PasswordChangeRequest, db: DbSession, current_user: Annotated[User, Depends(get_current_user)]) -> Response:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="기존 비밀번호가 일치하지 않습니다.")
    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(response: Response, db: DbSession, current_user: Annotated[User, Depends(get_current_user)]) -> Response:
    await db.delete(current_user)
    await db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/users")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/admin/users", response_model=list[UserResponse])
async def list_users(_: Annotated[User, Depends(get_admin_user)], db: DbSession, search: str | None = Query(default=None, max_length=255), department: Department | None = None) -> list[User]:
    statement = select(User)
    if search:
        statement = statement.where(or_(User.email.ilike(f"%{search}%"), User.name.ilike(f"%{search}%")))
    if department:
        statement = statement.where(User.department == department)
    return list((await db.scalars(statement.order_by(User.id))).all())


@router.patch("/admin/users/role", response_model=UserResponse)
async def update_role(payload: RoleUpdateRequest, db: DbSession, _: Annotated[User, Depends(get_admin_user)]) -> User:
    user = await db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
    user.role = payload.new_role
    await db.commit()
    await db.refresh(user)
    return user
