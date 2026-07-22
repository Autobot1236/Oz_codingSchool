from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import auth_settings, settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import Role
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories import refresh_token_repository, user_repository
from app.schemas.user import LoginRequest, SignupRequest


async def issue_refresh_token(
    session: AsyncSession, user_id: int, family_id: str | None = None
) -> str:
    raw_token = create_refresh_token()
    refresh_token_repository.add_refresh_token(
        session,
        RefreshToken(
            token_hash=hash_token(raw_token),
            family_id=family_id or str(uuid4()),
            user_id=user_id,
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            + timedelta(days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ),
    )
    return raw_token


async def rotate_refresh_token(
    session: AsyncSession, raw_token: str
) -> tuple[User, str]:
    row = await refresh_token_repository.get_refresh_token_with_user(
        session, hash_token(raw_token)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_INVALID", "message": "유효하지 않은 Refresh Token입니다."},
        )
    token, user = row
    now = datetime.now(UTC).replace(tzinfo=None)

    if token.revoked_at is not None:
        await refresh_token_repository.revoke_token_family(session, token.family_id, now)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_REUSED", "message": "Refresh Token 재사용이 감지되었습니다."},
        )
    if token.expires_at <= now:
        token.revoked_at = now
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_EXPIRED", "message": "Refresh Token이 만료되었습니다."},
        )
    if not user.is_active:
        token.revoked_at = now
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "비활성 계정입니다."},
        )

    replacement = await issue_refresh_token(session, token.user_id, token.family_id)
    token.revoked_at = now
    token.replaced_by_hash = hash_token(replacement)
    await session.commit()
    return user, replacement


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: int) -> None:
    await refresh_token_repository.revoke_user_tokens(
        session, user_id, datetime.now(UTC).replace(tzinfo=None)
    )


async def signup_user(session: AsyncSession, payload: SignupRequest) -> User:
    if await user_repository.get_user_by_email(session, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다.",
        )
    if await user_repository.phone_number_in_use(session, payload.phone_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        name=payload.name,
        department=payload.department,
        gender=payload.gender,
        phone_number=payload.phone_number,
        role=Role.PENDING,
        is_active=True,
    )
    user_repository.add_user(session, user)
    await session.commit()
    await session.refresh(user)
    return user


async def login_user(
    session: AsyncSession, payload: LoginRequest
) -> tuple[User, str, str]:
    user = await user_repository.get_user_by_email(session, payload.email)
    if user is None or not user.is_active or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = await issue_refresh_token(session, user.id)
    await session.commit()
    return user, access_token, refresh_token


async def logout_user(session: AsyncSession, user: User) -> None:
    await revoke_all_refresh_tokens(session, user.id)
    await session.commit()


async def refresh_user_access_token(
    session: AsyncSession, refresh_token: str
) -> tuple[str, str]:
    user, replacement = await rotate_refresh_token(session, refresh_token)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return access_token, replacement
