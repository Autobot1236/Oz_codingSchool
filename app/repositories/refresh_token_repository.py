from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User


def add_refresh_token(session: AsyncSession, refresh_token: RefreshToken) -> None:
    session.add(refresh_token)


async def get_refresh_token_with_user(
    session: AsyncSession, token_hash: str
) -> tuple[RefreshToken, User] | None:
    result = await session.execute(
        select(RefreshToken, User)
        .join(User, User.id == RefreshToken.user_id)
        .where(RefreshToken.token_hash == token_hash)
    )
    return result.one_or_none()


async def revoke_token_family(
    session: AsyncSession, family_id: str, revoked_at: datetime
) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )


async def revoke_user_tokens(
    session: AsyncSession, user_id: int, revoked_at: datetime
) -> None:
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=revoked_at)
    )
