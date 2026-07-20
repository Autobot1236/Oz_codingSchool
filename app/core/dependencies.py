from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_security import decode_access_token
from app.core.db.databases import async_get_db
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ACCESS_TOKEN_INVALID", "message": "인증이 필요합니다."},
        )
    try:
        user_id = int(decode_access_token(credentials.credentials)["user_id"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ACCESS_TOKEN_EXPIRED", "message": "Access Token이 만료되었습니다."},
        ) from exc
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ACCESS_TOKEN_INVALID", "message": "유효하지 않은 Access Token입니다."},
        ) from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "회원을 찾을 수 없습니다."})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_INACTIVE", "message": "비활성 계정입니다."})
    return user
