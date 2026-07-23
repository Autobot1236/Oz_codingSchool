# 4일차 User API 명세

모든 경로는 User/Auth API 계약에 따라 `/api/v1` 접두사를 사용한다. 인증이
필요한 요청은 다음 헤더를 사용한다.

```http
Authorization: Bearer <access_token>
```

## 인증 API

| 요구사항 | 메서드 · 경로 | 인증 | 설명 |
| --- | --- | --- | --- |
| REQ-USER-001 | `POST /api/v1/auth/signup` | 불필요 | 회원가입 |
| REQ-USER-002 | `POST /api/v1/auth/login` | 불필요 | 로그인 및 토큰 발급 |
| REQ-USER-003 | `POST /api/v1/auth/logout` | 필요 | 로그아웃 |
| NFR-USER-001 | `POST /api/v1/auth/refresh` | Refresh 쿠키 | 액세스/리프레시 토큰 재발급 |

### 회원가입 — `POST /api/v1/auth/signup`

```json
{
  "email": "doctor@example.com",
  "password": "Password123!",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phone_number": "01012345678"
}
```

- 성공: `201 Created`
- 이메일 또는 휴대폰 번호가 이미 있으면: `409 Conflict`
- 비밀번호는 8~20자이며 영문 대/소문자, 숫자, 특수문자를 각각 포함해야 한다.
- 계정은 `PENDING` 권한으로 생성되고 비밀번호는 해시로만 저장한다.

### 로그인 — `POST /api/v1/auth/login`

```json
{
  "email": "doctor@example.com",
  "password": "Password123!"
}
```

- 성공: `200 OK`, 응답 본문에 액세스 토큰과 사용자 정보가 포함된다.
- 성공 시 리프레시 토큰은 `HttpOnly`, `SameSite=Strict` 쿠키로
  `/api/v1/auth` 경로에 설정된다. 운영 HTTPS 환경에서는 `Secure=true`를 사용하고,
  로컬 HTTP 개발 환경에서는 `.env`의 `COOKIE_SECURE=false`로 설정한다.
- 이메일 또는 비밀번호가 맞지 않으면: `401 Unauthorized`

### 로그아웃 — `POST /api/v1/auth/logout`

- 성공: `200 OK`
- 인증된 사용자의 유효한 리프레시 토큰을 서버에서 폐기하고, `refresh_token`
  쿠키를 삭제한다.
- 인증 헤더가 없거나 유효하지 않으면: `401 Unauthorized`

### 토큰 재발급 — `POST /api/v1/auth/refresh`

- 요청 본문은 없으며 `refresh_token` 쿠키를 사용한다.
- 성공: `200 OK`. 액세스 토큰을 응답 본문에 반환하고, 리프레시 토큰은 회전시켜
  새 쿠키로 설정한다.

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```
- 액세스 토큰 만료: 30분, 리프레시 토큰 만료: 7일.
- 쿠키가 없거나 만료·재사용된 토큰이면: `401 Unauthorized`.

## 관리자 API

관리자 API는 모두 `ADMIN` 권한이 필요하다. 일반 사용자면 `403 Forbidden`,
미인증이면 `401 Unauthorized`를 반환한다.

| 요구사항 | 메서드 · 경로 | 설명 |
| --- | --- | --- |
| REQ-USER-004 | `GET /api/v1/users` | 회원 목록 조회 |
| REQ-USER-005 | `PATCH /api/v1/users/{user_id}/role` | 회원 권한 변경 |

### 회원 목록 조회 — `GET /api/v1/users`

선택 쿼리 파라미터는 `keyword`(이름 또는 이메일 검색), `department`
(`MEDICAL`, `DEV`, `RESEARCH`), `page`(기본 1), `size`(기본 10,
최대 100)다.

```json
{
  "users": [
    {
      "id": 1,
      "email": "doctor@example.com",
      "name": "홍길동",
      "department": "MEDICAL",
      "gender": "M",
      "phone_number": "01012345678",
      "role": "STAFF",
      "is_active": true
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

### 회원 권한 변경 — `PATCH /api/v1/users/{user_id}/role`

```json
{ "role": "STAFF" }
```

- `role`은 `PENDING`, `STAFF`, `ADMIN` 중 하나다.
- 성공: `200 OK`; 대상 사용자가 없으면 `404 Not Found`.

## 내 계정 API

| 요구사항 | 메서드 · 경로 | 설명 |
| --- | --- | --- |
| REQ-USER-006 | `GET /api/v1/users/me` | 내 프로필 조회 |
| REQ-USER-007 | `PATCH /api/v1/users/me` | 내 부서 또는 휴대폰 번호 수정 |
| REQ-USER-008 | `PATCH /api/v1/users/me/password` | 비밀번호 변경 |
| REQ-USER-009 | `DELETE /api/v1/users/me` | 회원탈퇴 |

모든 내 계정 API는 인증이 필요하며, 응답에 해시된 비밀번호를 포함하지 않는다.

### 내 프로필 조회 — `GET /api/v1/users/me`

- 성공: `200 OK`
- 이름, 이메일, 부서, 성별, 휴대폰 번호, 권한을 반환한다.

### 내 프로필 수정 — `PATCH /api/v1/users/me`

```json
{
  "department": "RESEARCH",
  "phone_number": "01098765432"
}
```

- 두 필드 중 하나 이상을 보내야 하며, 지원하지 않는 필드는 허용하지 않는다.
- 휴대폰 번호는 숫자 10~11자리이고 다른 계정과 중복될 수 없다.
- 성공: `200 OK`; 중복 번호는 `409 Conflict`.

### 비밀번호 변경 — `PATCH /api/v1/users/me/password`

```json
{
  "current_password": "Password123!",
  "new_password": "NewPassword123!"
}
```

- 기존 비밀번호를 검증한 뒤 새 비밀번호를 해시하여 저장한다.
- 성공: `204 No Content`. 기존의 리프레시 토큰을 폐기하고 쿠키를 삭제한다.

### 회원탈퇴 — `DELETE /api/v1/users/me`

- 성공: `204 No Content`
- 현재 사용자를 삭제하고, 남아 있는 리프레시 토큰도 폐기한다.

## 비기능 요구사항

- 평문 비밀번호와 토큰 원문은 데이터베이스에 저장하지 않는다.
- 모든 DB 접근은 `AsyncSession`과 `await`를 사용한다.
- Swagger UI는 `/docs`에서 위 API와 요청·응답 스키마를 확인할 수 있다.
