from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientDetailResponse,
    PatientListQuery,
    PatientListResponse,
    PatientResponse,
    PatientUpdateRequest,
)
from app.services import patient_service

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="환자 정보 등록",
)
async def create_patient(
    payload: PatientCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientResponse:
    return await patient_service.create_patient(
        session=session,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=PatientListResponse,
    summary="환자 목록 조회",
)
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


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="환자 정보 수정",
)
async def update_patient(
    patient_id: int,
    payload: PatientUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> PatientResponse:
    return await patient_service.update_patient(
        session=session,
        patient_id=patient_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="환자 정보 삭제",
)
async def delete_patient(
    patient_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(async_get_db)],
) -> None:
    await patient_service.delete_patient(
        session=session,
        patient_id=patient_id,
        current_user=current_user,
    )
