from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timedelta
from typing import Annotated

from app.core.db.databases import async_get_db
from app.core.security import hash_password, create_access_token, verify_password
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import SignupRequest, UserResponse, LoginRequest, LoginResponse, LoginUserResponse
from app.schemas.auth import AccessTokenData, AccessTokenResponse
from app.services.auth_service import rotate_refresh_token
from app.core.config import settings, auth_settings

router = APIRouter(prefix="/auth", tags=["auth"])


# 1. 회원가입 (REQ-USER-001)
@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    data: SignupRequest, db: AsyncSession = Depends(async_get_db)
) -> User:
    # 이메일 중복 검증
    email_exists = await db.scalar(select(User.id).where(User.email == data.email))
    if email_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    # 휴대폰 번호 중복 검증
    phone_exists = await db.scalar(
        select(User.id).where(User.phone_number == data.phone_number)
    )
    if phone_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 휴대폰 번호입니다.",
        )

    # 계정 생성 (role은 항상 PENDING 고정)
    new_user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        name=data.name,
        department=data.department,
        gender=data.gender,
        phone_number=data.phone_number,
        role=Role.PENDING,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# 2. 로그인 (REQ-USER-002)
@router.post(
    "/login",
    response_model=LoginResponse,
    summary="로그인",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(async_get_db),
) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return LoginResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=LoginUserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.name,
        ),
    )
  
# 3. 로그아웃 (REQ-USER-003)
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    # httpOnly 쿠키로 전달된 refresh_token 만료 처리
    # /auth/refresh 에서 쿠키를 path="/api/v1/auth", samesite=auth_settings.COOKIE_SAMESITE 로 설정하므로
    # 삭제할 때도 동일한 path/samesite를 지정해야 브라우저가 같은 쿠키로 인식해서 실제로 지워진다.
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite=auth_settings.COOKIE_SAMESITE,
        secure=auth_settings.COOKIE_SECURE,
    )
    return {"detail": "성공적으로 로그아웃되었습니다."}
  
 # 4. 토큰 재발급 (NFR-USER-001)  
@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    response: Response,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> AccessTokenResponse:
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_MISSING", "message": "Refresh Token이 없습니다."},
        )

    user, replacement = await rotate_refresh_token(db, refresh_token)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(seconds=expires_in),
    )
    response.set_cookie(
        key="refresh_token",
        value=replacement,
        max_age=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=auth_settings.COOKIE_SECURE,
        samesite=auth_settings.COOKIE_SAMESITE,
        path="/api/v1/auth",
    )
    return AccessTokenResponse(
        data=AccessTokenData(accessToken=access_token, expiresIn=expires_in)
    )