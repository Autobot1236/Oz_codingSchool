from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import require_admin
from app.schemas.user import AdminUserListResponse, UserRoleResponse, UserRoleUpdateRequest
from app.services import admin_service

router = APIRouter(
    prefix="/api/v1/users",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AdminUserListResponse, summary="회원 목록 조회")
async def list_users(
    keyword: str | None = Query(default=None, max_length=100),
    department: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(async_get_db),
) -> AdminUserListResponse:
    return await admin_service.list_users(session, keyword, department, page, size)


@router.patch(
    "/{user_id}/role",
    response_model=UserRoleResponse,
    summary="회원 권한 변경",
)
async def update_user_role(
    user_id: int,
    payload: UserRoleUpdateRequest,
    session: AsyncSession = Depends(async_get_db),
) -> UserRoleResponse:
    return await admin_service.update_user_role(session, user_id, payload.role)
