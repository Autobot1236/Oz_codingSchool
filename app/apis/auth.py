from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import auth_settings, settings
from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.auth import RefreshAccessTokenResponse
from app.schemas.user import LoginRequest, LoginResponse, LoginUserResponse, SignupRequest, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=auth_settings.COOKIE_SECURE,
        samesite=auth_settings.COOKIE_SAMESITE,
        path="/api/v1/auth",
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest, session: AsyncSession = Depends(async_get_db)
) -> User:
    return await auth_service.signup_user(session, payload)


@router.post("/login", response_model=LoginResponse, summary="로그인")
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(async_get_db),
) -> LoginResponse:
    user, access_token, refresh_token = await auth_service.login_user(session, payload)
    set_refresh_cookie(response, refresh_token)
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


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    await auth_service.logout_user(session, current_user)
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
        secure=auth_settings.COOKIE_SECURE,
    )
    return {"detail": "성공적으로 로그아웃되었습니다."}


@router.post("/refresh", response_model=RefreshAccessTokenResponse)
async def refresh_access_token(
    response: Response,
    session: Annotated[AsyncSession, Depends(async_get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> RefreshAccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_MISSING", "message": "Refresh Token이 없습니다."},
        )

    access_token, replacement_token = await auth_service.refresh_user_access_token(
        session, refresh_token
    )
    set_refresh_cookie(response, replacement_token)
    return RefreshAccessTokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
