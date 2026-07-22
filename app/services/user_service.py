from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.enums import Department, Role
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import PasswordChangeRequest, UserProfileResponse, UserProfileUpdateRequest
from app.services.auth_service import revoke_all_refresh_tokens


def to_profile_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        name=user.name,
        email=user.email,
        department=user.department.name,
        gender=user.gender.name,
        phone_number=user.phone_number,
        role=user.role.name,
    )


async def change_password(
    session: AsyncSession, user: User, payload: PasswordChangeRequest
) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "CURRENT_PASSWORD_MISMATCH", "message": "기존 비밀번호가 일치하지 않습니다."},
        )
    if verify_password(payload.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PASSWORD_REUSE_NOT_ALLOWED", "message": "기존 비밀번호는 재사용할 수 없습니다."},
        )

    user.hashed_password = hash_password(payload.new_password)
    await revoke_all_refresh_tokens(session, user.id)
    await session.commit()


async def update_profile(
    session: AsyncSession, user: User, payload: UserProfileUpdateRequest
) -> UserProfileResponse:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 부서 또는 휴대폰 번호를 입력해 주세요.",
        )

    department = user.department
    if payload.department is not None:
        try:
            department = Department[payload.department.upper()]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="department는 MEDICAL, DEV, RESEARCH 중 하나여야 합니다.",
            ) from exc

    if payload.phone_number is not None and await user_repository.phone_number_in_use(
        session, payload.phone_number, user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        )

    user.department = department
    if payload.phone_number is not None:
        user.phone_number = payload.phone_number

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        ) from exc

    return to_profile_response(user)


async def delete_account(session: AsyncSession, user: User) -> None:
    await revoke_all_refresh_tokens(session, user.id)
    await user_repository.delete_user(session, user)
    await session.commit()
