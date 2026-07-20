from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_config import auth_settings
from app.core.auth_dependencies import get_current_user
from app.core.auth_security import hash_password, verify_password
from app.core.db.databases import async_get_db
from app.models.user import User
from app.schemas.user import PasswordChangeRequest
from app.services.auth_service import revoke_all_refresh_tokens


router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChangeRequest,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    if not verify_password(payload.currentPassword, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "CURRENT_PASSWORD_MISMATCH", "message": "기존 비밀번호가 일치하지 않습니다."},
        )
    if verify_password(payload.newPassword, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PASSWORD_REUSE_NOT_ALLOWED", "message": "기존 비밀번호는 재사용할 수 없습니다."},
        )

    user.hashed_password = hash_password(payload.newPassword)
    await revoke_all_refresh_tokens(db, user.id)
    await db.commit()

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=auth_settings.COOKIE_SECURE,
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
    )
