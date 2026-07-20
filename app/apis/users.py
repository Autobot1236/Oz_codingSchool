from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import auth_settings
from app.core.dependencies import get_current_user
from app.core.security import hash_password, verify_password, require_admin
from app.core.db.databases import async_get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import PasswordChangeRequest, RoleUpdateRequest, UserRoleResponse
from app.services.auth_service import revoke_all_refresh_tokens

router = APIRouter(prefix="/users", tags=["users"])

# 1. 회원 권한 변경 (REQ-USER-005)
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

# 2. 비밀 번호 변경 (REQ-USER-008)  
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