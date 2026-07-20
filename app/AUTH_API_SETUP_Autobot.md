# 인증 API 신규 파일 적용 안내

이 묶음은 기존 저장소 파일을 포함하거나 덮어쓰지 않으며, 모두 신규 파일입니다.

## 제공 API

- `POST /api/v1/auth/refresh`
- `PATCH /api/v1/users/me/password`

## 1. 파일 추가

압축을 저장소 루트에서 해제합니다.

## 2. 의존성 설치

`auth_requirements.txt`의 다음 패키지를 프로젝트 의존성에 추가합니다.

```bash
uv add "PyJWT>=2.10.1" "pwdlib[argon2]>=0.3.0"
```

## 3. 라우터 등록

기존 파일을 자동으로 수정하지 않았습니다. 서비스에 API를 노출하려면 `app/main.py`에 다음 내용을 직접 추가해야 합니다.

```python
from app.apis import auth_apis, user_apis

app.include_router(auth_apis.router)
app.include_router(user_apis.router)
```

## 4. 환경변수

```dotenv
JWT_SECRET_KEY=충분히-긴-임의의-비밀키
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=true
COOKIE_SAMESITE=strict
```

로컬 HTTP 테스트에서만 `COOKIE_SECURE=false`를 사용합니다.

## 5. 마이그레이션

```bash
uv run alembic upgrade head
```

## 로그인 API 연결

로그인 성공 시 아래 함수를 호출해 Refresh Token을 만들고 DB를 커밋한 뒤, 반환된 원문을 `refresh_token` HttpOnly 쿠키로 설정해야 합니다.

```python
from app.services.auth_service import issue_refresh_token

refresh_token = await issue_refresh_token(db, user.id)
await db.commit()
```

비밀번호 변경 시 기존 Refresh Token은 모두 폐기됩니다. 기존 User 모델을 수정하지 않는 조건에 따라 변경 전에 발급된 Access Token은 남은 만료시간 동안 유효하며 최대 30분 후 만료됩니다.
