from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Department, Role
from app.repositories import user_repository
from app.schemas.user import AdminUserListItem, AdminUserListResponse, UserRoleResponse


async def list_users(
    session: AsyncSession,
    keyword: str | None,
    department_value: str | None,
    page: int,
    size: int,
) -> AdminUserListResponse:
    department = None
    if department_value:
        try:
            department = Department[department_value.upper()]
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="department는 MEDICAL, DEV, RESEARCH 중 하나여야 합니다.",
            ) from exc

    users, total = await user_repository.list_users(
        session, keyword, department, page, size
    )
    return AdminUserListResponse(
        users=[
            AdminUserListItem(
                id=user.id,
                email=user.email,
                name=user.name,
                department=user.department.name,
                gender=user.gender.name,
                phone_number=user.phone_number,
                role=user.role.name,
                is_active=user.is_active,
            )
            for user in users
        ],
        page=page,
        size=size,
        total=total,
    )


async def update_user_role(
    session: AsyncSession, user_id: int, role_value: str
) -> UserRoleResponse:
    try:
        role = Role[role_value]
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role은 PENDING, STAFF, ADMIN 중 하나여야 합니다.",
        ) from exc

    user = await user_repository.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="회원을 찾을 수 없습니다.",
        )

    user.role = role
    await session.commit()
    await session.refresh(user)
    return UserRoleResponse(id=user.id, email=user.email, name=user.name, role=user.role.name)
