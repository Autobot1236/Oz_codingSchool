from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import auth_settings
from app.core.security import hash_password, verify_password, get_current_user
from app.core.db.databases import async_get_db
from app.models.enums import Department
from app.models.user import User
from app.services.auth_service import revoke_all_refresh_tokens
from app.schemas.user import (
    UserProfileResponse,
    UserProfileUpdateRequest,
    PasswordChangeRequest
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _to_profile_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        name=user.name,
        email=user.email,
        department=user.department.name,
        gender=user.gender.name,
        phone_number=user.phone_number,
        role=user.role.name,
    )


# 1. 비밀 번호 변경 (REQ-USER-008)
@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChangeRequest,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "CURRENT_PASSWORD_MISMATCH", "message": "기존 비밀번호가 일치하지 않습니다."},
        )
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PASSWORD_REUSE_NOT_ALLOWED", "message": "기존 비밀번호는 재사용할 수 없습니다."},
        )

    user.hashed_password = hash_password(payload.new_password)
    await revoke_all_refresh_tokens(db, user.id)
    await db.commit()

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=auth_settings.COOKIE_SECURE,
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
      )
    
    
# 2. 마이페이지 조회 (REQ-USER-006)
@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="마이페이지 조회",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return _to_profile_response(current_user)


# REQ-USER-009: 회원 탈퇴
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> None:
    await revoke_all_refresh_tokens(db, current_user.id)
    await db.delete(current_user)
    await db.commit()


# 3. 회원 정보 수정 (REQ-USER-007)
@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="회원 정보 부분 수정",
)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 부서 또는 휴대폰 번호를 입력해 주세요.",
        )

    new_department = current_user.department
    if payload.department is not None:
        try:
            department_name = payload.department.upper()
            new_department = Department[department_name]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "department는 MEDICAL, DEV, RESEARCH 중 "
                    "하나여야 합니다."
                ),
            ) from exc

    if payload.phone_number is not None:
        result = await db.execute(
            select(User.id).where(
                User.phone_number == payload.phone_number,
                User.id != current_user.id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 휴대폰 번호입니다.",
            )

    current_user.department = new_department
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        ) from exc

    return _to_profile_response(current_user)
