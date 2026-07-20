from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.core.passwords import hash_password
from app.models.enums import Department, Gender, Role
from app.models.user import User
from app.repositories.user_repository import (
    get_user_by_email,
    get_user_by_phone_number,
)
from app.schemas.user_registration import UserSignupRequest


async def _ensure_unique_user_fields(
    db: AsyncSession,
    *,
    email: str,
    phone_number: str,
) -> None:
    if await get_user_by_email(db, email) is not None:
        raise APIError(
            status_code=409,
            code="EMAIL_ALREADY_EXISTS",
            message="이미 가입된 이메일입니다.",
        )
    if await get_user_by_phone_number(db, phone_number) is not None:
        raise APIError(
            status_code=409,
            code="PHONE_NUMBER_ALREADY_EXISTS",
            message="이미 가입된 휴대폰 번호입니다.",
        )


async def register_user(
    db: AsyncSession,
    payload: UserSignupRequest,
) -> User:
    await _ensure_unique_user_fields(
        db,
        email=str(payload.email),
        phone_number=payload.phone_number,
    )

    user = User(
        email=str(payload.email),
        hashed_password=hash_password(payload.password),
        name=payload.name,
        phone_number=payload.phone_number,
        gender=Gender[payload.gender.value],
        department=Department[payload.department.value],
        role=Role.PENDING,
        is_active=True,
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        await _ensure_unique_user_fields(
            db,
            email=str(payload.email),
            phone_number=payload.phone_number,
        )
        raise APIError(
            status_code=409,
            code="USER_CREATE_CONFLICT",
            message="회원 정보를 저장하는 중 충돌이 발생했습니다.",
        ) from exc

    await db.refresh(user)
    return user
