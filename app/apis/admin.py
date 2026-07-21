from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.core.db.databases import async_get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import RoleUpdateRequest, UserRoleResponse

# 관리자 전용 API. 이 라우터 밑의 모든 엔드포인트는 require_admin을 통과해야
# 접근할 수 있다 (각 엔드포인트마다 개별로 걸지 않고 라우터 레벨에서 한 번에 적용).
router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
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
