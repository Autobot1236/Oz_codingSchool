from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth_config import auth_settings
from app.core.auth_security import create_refresh_token, hash_token
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def issue_refresh_token(
    db: AsyncSession, user_id: int, family_id: str | None = None
) -> str:
    raw_token = create_refresh_token()
    db.add(
        RefreshToken(
            token_hash=hash_token(raw_token),
            family_id=family_id or str(uuid4()),
            user_id=user_id,
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            + timedelta(days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return raw_token


async def rotate_refresh_token(
    db: AsyncSession, raw_token: str
) -> tuple[User, str]:
    row = (
        await db.execute(
            select(RefreshToken, User)
            .join(User, User.id == RefreshToken.user_id)
            .where(RefreshToken.token_hash == hash_token(raw_token))
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_INVALID", "message": "유효하지 않은 Refresh Token입니다."},
        )
    token, user = row

    now = datetime.now(UTC).replace(tzinfo=None)
    if token.revoked_at is not None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == token.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_REUSED", "message": "Refresh Token 재사용이 감지되었습니다."},
        )
    if token.expires_at <= now:
        token.revoked_at = now
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_EXPIRED", "message": "Refresh Token이 만료되었습니다."},
        )
    if not user.is_active:
        token.revoked_at = now
        await db.commit()
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_INACTIVE", "message": "비활성 계정입니다."})

    replacement = await issue_refresh_token(db, token.user_id, token.family_id)
    token.revoked_at = now
    token.replaced_by_hash = hash_token(replacement)
    await db.commit()
    return user, replacement


async def revoke_all_refresh_tokens(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC).replace(tzinfo=None))
    )
