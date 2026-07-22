from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Department
from app.models.user import User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def phone_number_in_use(
    session: AsyncSession, phone_number: str, excluded_user_id: int | None = None
) -> bool:
    statement = select(User.id).where(User.phone_number == phone_number)
    if excluded_user_id is not None:
        statement = statement.where(User.id != excluded_user_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def list_users(
    session: AsyncSession,
    keyword: str | None,
    department: Department | None,
    page: int,
    size: int,
) -> tuple[list[User], int]:
    conditions = []
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        conditions.append(or_(User.email.ilike(pattern), User.name.ilike(pattern)))
    if department is not None:
        conditions.append(User.department == department)

    users_result = await session.execute(
        select(User)
        .where(*conditions)
        .order_by(User.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    total_result = await session.execute(
        select(func.count()).select_from(User).where(*conditions)
    )
    return users_result.scalars().all(), total_result.scalar_one()


def add_user(session: AsyncSession, user: User) -> None:
    session.add(user)


async def delete_user(session: AsyncSession, user: User) -> None:
    await session.delete(user)
