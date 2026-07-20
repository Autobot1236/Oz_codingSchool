from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_config import auth_settings
from app.core.db.databases import async_get_db
from app.core.auth_security import create_access_token
from app.schemas.auth import AccessTokenData, AccessTokenResponse
from app.services.auth_service import rotate_refresh_token


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_MISSING", "message": "Refresh Token이 없습니다."},
        )

    user, replacement = await rotate_refresh_token(db, refresh_token)
    access_token, expires_in = create_access_token(user.id)
    response.set_cookie(
        key="refresh_token",
        value=replacement,
        max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=auth_settings.COOKIE_SECURE,
        samesite=auth_settings.COOKIE_SAMESITE,
        path="/api/v1/auth",
    )
    return AccessTokenResponse(
        data=AccessTokenData(accessToken=access_token, expiresIn=expires_in)
    )
