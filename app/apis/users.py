from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db.databases import async_get_db
from app.core.security import create_access_token, require_admin, verify_password
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import (
    LoginRequest,
    LoginResponse,
    LoginUserResponse,
    RoleUpdateRequest,
    UserRoleResponse,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/users", tags=["users"])


@auth_router.post(
    "/login",
    response_model=LoginResponse,
    summary="로그인",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(async_get_db),
) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return LoginResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=LoginUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.name,
        ),
    )


@router.patch(
    "/{user_id}/role",
    response_model=UserRoleResponse,
    summary="회원 권한 변경",
)
async def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
    _: User = Depends(require_admin),
) -> UserRoleResponse:
    try:
        new_role = Role[payload.role]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role은 PENDING, STAFF, ADMIN 중 하나여야 합니다.",
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회원을 찾을 수 없습니다.",
        )

    user.role = new_role
    await db.commit()
    await db.refresh(user)

    return UserRoleResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.name,
    )

