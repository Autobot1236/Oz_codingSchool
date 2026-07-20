from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.databases import async_get_db
from app.core.security import get_password_hash
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import SignupRequest, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


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
        hashed_password=get_password_hash(data.password),
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


# 2. 로그아웃 (REQ-USER-003)
@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(response: Response):
    # httpOnly 쿠키로 전달된 refresh_token 만료 처리
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="lax",
        secure=True,  # 프로덕션 HTTPS 환경 기준
    )
    return {"detail": "성공적으로 로그아웃되었습니다."}
