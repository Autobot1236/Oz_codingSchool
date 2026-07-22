from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import auth_settings
from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import PasswordChangeRequest, UserProfileResponse, UserProfileUpdateRequest
from app.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChangeRequest,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    await user_service.change_password(session, user, payload)
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=auth_settings.COOKIE_SECURE,
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
    )


@router.get("/me", response_model=UserProfileResponse, summary="마이페이지 조회")
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return user_service.to_profile_response(current_user)


@router.patch("/me", response_model=UserProfileResponse, summary="회원 정보 부분 수정")
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    session: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return await user_service.update_profile(session, current_user, payload)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(async_get_db),
) -> None:
    await user_service.delete_account(session, current_user)
