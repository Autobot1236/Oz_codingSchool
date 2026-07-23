from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.patient import (
    PatientDetailResponse,
    PatientListQuery,
    PatientListResponse,
)
from app.services import patient_service

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.get("", response_model=PatientListResponse, summary="환자 목록 조회")
async def list_patients(
    query: Annotated[PatientListQuery, Query()],
    _current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientListResponse:
    return await patient_service.list_patients(session, query)


@router.get(
    "/{patient_id}",
    response_model=PatientDetailResponse,
    summary="환자 상세 조회",
)
async def get_patient_detail(
    patient_id: int,
    _current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientDetailResponse:
    return await patient_service.get_patient_detail(session, patient_id)

