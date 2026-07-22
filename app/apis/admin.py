from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.core.db.databases import async_get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import (
    AdminUserListItem,
    AdminUserListResponse,
    RoleUpdateRequest,
    UserRoleResponse,
)

# 관리자 전용 API. 이 라우터 밑의 모든 엔드포인트는 require_admin을 통과해야
# 접근할 수 있다 (각 엔드포인트마다 개별로 걸지 않고 라우터 레벨에서 한 번에 적용).
router = APIRouter(
    prefix="/api/v1/users",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# REQ-USER-004: 회원 목록 조회 (관리자)
@router.get("", response_model=AdminUserListResponse, summary="회원 목록 조회")
async def list_users(
    keyword: str | None = Query(default=None, max_length=100),
    department: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(async_get_db),
) -> AdminUserListResponse:
    conditions = []
    if keyword:
        pattern = f"%{keyword.strip()}%"
        conditions.append(or_(User.email.ilike(pattern), User.name.ilike(pattern)))

    if department:
        department_name = department.upper()
        try:
            conditions.append(User.department == Department[department_name])
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="department는 MEDICAL, DEV, RESEARCH 중 하나여야 합니다.",
            ) from exc

    users_result = await db.execute(
        select(User)
        .where(*conditions)
        .order_by(User.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    total_result = await db.execute(select(func.count()).select_from(User).where(*conditions))
    users = users_result.scalars().all()

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
        total=total_result.scalar_one(),
    )


# 1. 회원 권한 변경 (REQ-USER-005)
@router.patch(
    "/{user_id}/role",
    response_model=UserRoleResponse,
    summary="회원 권한 변경",
)
async def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: AsyncSession = Depends(async_get_db),
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
