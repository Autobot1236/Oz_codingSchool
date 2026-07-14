import re
from fastapi import APIRouter, Path
from pydantic import BaseModel, Field, field_validator

# 1. FastAPI 라우터
router = APIRouter()

# 2. 초기 데이터셋
user_list = [
  {
    "id": 1,
    "name": "홍길동",
    "age": 24,
    "email": "gildong24@example.com",
    "password": "Password1234!!",
  },
  {
    "id": 2,
    "name": "장문복",
    "age": 21,
    "email": "moonluck12@example.com",
    "password": "Check1321!",
  },
  {
    "id": 3,
    "name": "임우진",
    "age": 31,
    "email": "limousine33@example.com",
    "password": "lwsPAssword12@",
  },
]

# 이메일 검증 정규표현식
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


# --- Response Schemas (출력용 모델) ---
class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str


# --- Request Schemas (입력 검증용 모델) ---
class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=10)
    age: int = Field(..., ge=14)
    email: str = Field(..., max_length=30)
    password: str = Field(..., min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
      if not re.match(EMAIL_REGEX, v):
        raise ValueError("올바르지 않은 이메일 형식입니다.")
      
      # 중복 검사 (얼리 리턴 스타일 예외 발생)
      if any(user["email"] == v for user in user_list):
        raise ValueError("이미 등록된 이메일입니다.")
      
      return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
      # 대소문자 및 특수문자 포함 검증
      has_upper = any(c.isupper() for c in v)
      has_lower = any(c.islower() for c in v)
      has_special = any(not c.isalnum() for c in v)

      if not (has_upper and has_lower and has_special):
        raise ValueError(
          "비밀번호는 대소문자와 특수문자가 각각 최소 1개 이상 포함되어야 합니다."
        )
      
      return v


class UserUpdateRequest(BaseModel):
    age: int | None = Field(None, ge=14)
    email: str | None = Field(None, max_length=30)
    password: str | None = Field(None, min_length=8, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
      if v is None:
        return v
      
      if not re.match(EMAIL_REGEX, v):
        raise ValueError("올바르지 않은 이메일 형식입니다.")
      
      return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
      if v is None:
        return v

      has_upper = any(c.isupper() for c in v)
      has_lower = any(c.islower() for c in v)
      has_special = any(not c.isalnum() for c in v)

      if not (has_upper and has_lower and has_special):
        raise ValueError(
          "비밀번호는 대소문자와 특수문자가 각각 최소 1개 이상 포함되어야 합니다."
        )
        
      return v


# --- API Endpoints ---

# 1. 모든 회원의 정보를 목록으로 조회하는 API
@router.get("/practice_api/users", response_model=list[UserResponse])
def get_all_users():
  return user_list


# 2. 특정 회원의 정보를 조회하는 API (얼리 리턴 적용)
@router.get("/practice_api/users/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int = Path(..., description="조회할 회원의 ID")):
  for user in user_list:
    if user["id"] == user_id:
      return user
    
  # 루프를 끝까지 돌았는데 유저가 없으면 바로 실패 결과 반환
  return {"detail": "해당 ID의 회원을 찾을 수 없습니다."}


# 3. 회원의 정보를 추가하는 API
@router.post("/practice_api/users", response_model=UserResponse, status_code=201)
def create_user(user_data: UserCreateRequest):
  new_id = max([user["id"] for user in user_list], default=0) + 1

  new_user = {
    "id": new_id,
    "name": user_data.name,
    "age": user_data.age,
    "email": user_data.email,
    "password": user_data.password,
  }
  user_list.append(new_user)
  return new_user


# 4. 회원의 정보를 수정하는 API (얼리 리턴 적용)
@router.patch("/practice_api/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, update_data: UserUpdateRequest):
  # [얼리 리턴 1] 입력 데이터가 아예 없는 경우 최상단에서 컷
  update_dict = update_data.model_dump(exclude_unset=True)
  if not update_dict:
    return {"detail": "수정할 항목을 최소 하나 이상 입력해야 합니다."}

  # [얼리 리턴 2] 수정 대상 유저 탐색 및 존재 여부 검증
  target_user = None
  for user in user_list:
    if user["id"] == user_id:
      target_user = user
      break

  if not target_user:
    return {"detail": "해당 ID의 회원을 찾을 수 없습니다."}

  # [얼리 리턴 3] 이메일 수정 요청이 있고, 중복이 발견되면 바로 컷
  if update_data.email is not None:
    for user in user_list:
      if user["email"] == update_data.email and user["id"] != user_id:
        return {"detail": "이미 사용 중인 이메일입니다."}

    # 모든 검증을 통과한 뒤 최종 수정 반영 및 반환
  for key, value in update_dict.items():
    target_user[key] = value

  return target_user


# 5. 특정 회원의 정보를 삭제하는 API (얼리 리턴 적용)
@router.delete("/practice_api/users/{user_id}")
def delete_user(user_id: int):
  for index, user in enumerate(user_list):
    if user["id"] == user_id:
      user_list.pop(index)
      return {"message": "삭제가 완료되었습니다."}

  # 루프 내에서 매칭되어 삭제·리턴되지 않았다면 유효하지 않은 ID이므로 실패 결과 반환
  return {"detail": "해당 ID의 회원을 찾을 수 없습니다."}