from datetime import timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.models.user import User
from app.schemas.user_registration import (
    UserSignupData,
    UserSignupRequest,
    UserSignupResponse,
)
from app.services.user_registration_service import register_user


router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _to_signup_data(user: User) -> UserSignupData:
    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return UserSignupData(
        id=user.id,
        email=user.email,
        name=user.name,
        department=user.department.name,
        gender=user.gender.name,
        phone_number=user.phone_number,
        role=user.role.name,
        active=user.is_active,
        created_at=created_at,
    )


@router.post(
    "",
    response_model=UserSignupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="사내 구성원 계정을 PENDING 권한으로 생성합니다.",
)
async def signup(
    payload: UserSignupRequest,
    db: AsyncSession = Depends(async_get_db),
) -> UserSignupResponse:
    user = await register_user(db, payload)
    return UserSignupResponse(data=_to_signup_data(user))
