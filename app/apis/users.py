from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user, require_admin
from app.models.enums import Department, Role
from app.models.user import User
from app.schemas.user import (
    RoleUpdateRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserRoleResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


def _to_profile_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        name=user.name,
        email=user.email,
        department=user.department.name,
        gender=user.gender.name,
        phone_number=user.phone_number,
        role=user.role.name,
    )


# 6. 마이페이지 조회 (REQ-USER-006)
@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="마이페이지 조회",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return _to_profile_response(current_user)


# 7. 회원 정보 수정 (REQ-USER-007)
@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="회원 정보 부분 수정",
)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="수정할 부서 또는 휴대폰 번호를 입력해 주세요.",
        )

    new_department = current_user.department
    if payload.department is not None:
        try:
            department_name = payload.department.upper()
            if department_name == "DEVELOPMENT":
                department_name = "DEV"
            new_department = Department[department_name]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "department는 MEDICAL, DEV(DEVELOPMENT), RESEARCH 중 "
                    "하나여야 합니다."
                ),
            ) from exc

    if payload.phone_number is not None:
        result = await db.execute(
            select(User.id).where(
                User.phone_number == payload.phone_number,
                User.id != current_user.id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 휴대폰 번호입니다.",
            )

    current_user.department = new_department
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 휴대폰 번호입니다.",
        ) from exc

    return _to_profile_response(current_user)


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
