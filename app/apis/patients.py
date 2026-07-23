from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.patient import PatientListQuery, PatientListResponse
from app.services import patient_service

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("", response_model=PatientListResponse, summary="환자 목록 조회")
async def list_patients(
    query: Annotated[PatientListQuery, Query()],
    _current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientListResponse:
    return await patient_service.list_patients(session, query)
