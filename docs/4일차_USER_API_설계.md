# API 명세서 — User(회원·인증) 도메인

> **대상 서비스:** 사내 흉부 X-Ray AI 진단 서비스
> **근거 문서:** 사용자 요구사항 정의서 (REQ-USER-001 ~ 009, NFR-USER-001 ~ 003)
> **양식:** 제공받은 「API 명세서 예시」 포맷 준수
> **작성 원칙:** 정의서에 명시된 내용을 기준으로 설계. 정의서에 없는 항목은 새로 만들지 않되, API 명세에 기본적으로 필요한 요소(HTTP 상태 코드·에러 응답·인증 헤더 등)만 정의함.

---

## 0. 공통 규약

### 0.1 기본 정보

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 데이터 포맷 | `application/json` (UTF-8) |
| 인증 방식 | JWT (Access Token, Bearer) — 근거: NFR-USER-001 |
| Access Token 만료 | 30분 — 근거: NFR-USER-001 |
| Refresh Token 만료 | 7일, `http_only` 쿠키로 전달 — 근거: NFR-USER-001 |
| JWT 페이로드 | `user_id`만 저장 (최소식별) — 근거: NFR-USER-001 |
| 응답 시간 | 모든 유저 API 3초 이내 처리·응답 — 근거: NFR-USER-003 |

### 0.2 권한 등급 (근거: REQ-USER-005 비고)

| 권한 | 접근 범위 |
| --- | --- |
| 대기자 | 마이페이지 외 모든 서비스 접근 불가 |
| 스태프 | 흉부 X-ray 관련 모든 읽기·쓰기·수정 |
| 어드민 | 모든 항목 데이터 접근 (시스템 관리자) |

> 회원가입 시 기본 권한은 **대기자**로 부여한다.

### 0.3 부서 / 성별 값 (근거: REQ-USER-001)

| 구분 | 값 |
| --- | --- |
| 부서 | 연구 / 의료 / 개발 |
| 성별 | M / F |

### 0.4 공통 에러 응답

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "이메일 또는 비밀번호가 올바르지 않습니다."
  }
}
```

| 상태 코드 | 의미 |
| --- | --- |
| 400 Bad Request | 필수값 누락 / 형식 오류 |
| 401 Unauthorized | 미인증 / 토큰 만료·무효 |
| 403 Forbidden | 권한 부족 |
| 404 Not Found | 대상 리소스 없음 |
| 409 Conflict | 중복(예: 이메일 중복 가입) |

---

## 1. 회원가입 (REQ-USER-001)

### 1.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원가입 API |
| 설명 | 사내 의료인·개발 실무진의 회원가입 |
| 엔드포인트(Endpoint) | `/api/v1/auth/signup` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |

### 1.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |

**본문 예시**

```json
{
  "email": "user@hospital.com",
  "password": "myPassword",
  "name": "홍길동",
  "department": "의료",
  "gender": "M",
  "phone": "010-1234-5678"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일 (로그인 ID) |
| password | string | Y | 비밀번호 |
| name | string | Y | 이름 |
| department | string | Y | 부서 (연구/의료/개발) |
| gender | string | Y | 성별 (M/F) |
| phone | string | Y | 휴대폰 번호 |

### 1.3 응답(Response)

**성공 — 201 Created**

```json
{
  "id": 1,
  "email": "user@hospital.com",
  "name": "홍길동",
  "department": "의료",
  "gender": "M",
  "phone": "010-1234-5678",
  "role": "대기자",
  "is_active": true
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 회원 고유 ID |
| role | string | 권한 (가입 시 기본값: 대기자) |
| is_active | boolean | 계정 활성화 여부 |

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 400 | 필수값 누락 / 형식 오류 |
| 409 | 이메일 중복 |

---

## 2. 로그인 (REQ-USER-002 / NFR-USER-001)

### 2.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 로그인 API |
| 설명 | 이메일·비밀번호를 활용한 로그인 및 토큰 발급 |
| 엔드포인트(Endpoint) | `/api/v1/auth/login` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |

### 2.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |

**본문 예시**

```json
{
  "email": "user@hospital.com",
  "password": "myPassword"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일 |
| password | string | Y | 사용자 비밀번호 |

### 2.3 응답(Response)

**성공 — 200 OK**

```json
{
  "access_token": "eyJhbGci...",
  "user": {
    "id": 1,
    "email": "user@hospital.com",
    "name": "홍길동",
    "role": "스태프"
  }
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| access_token | string | JWT 액세스 토큰 (만료 30분) |
| user.id | integer | 회원 고유 ID |
| user.role | string | 권한 등급 |

> 📌 **예시 양식과의 의도적 차이:** 제공된 예시는 `refresh_token`을 응답 본문에 담았으나, **NFR-USER-001에 따라 refresh_token은 본문에 넣지 않고 `Set-Cookie`(http_only)로 전달**한다.
> `Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Max-Age=604800`

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 400 | 필수값 누락 |
| 401 | 이메일/비밀번호 불일치 |

---

## 3. 토큰 재발급 (NFR-USER-001)

### 3.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 액세스 토큰 재발급 API |
| 설명 | 만료된 액세스 토큰을 refresh 토큰으로 재발급 |
| 엔드포인트(Endpoint) | `/api/v1/auth/refresh` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N (refresh 쿠키로 검증) |

### 3.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Cookie | refresh_token=... | http_only 쿠키 (자동 전송) |

> 본문 없음. refresh_token은 http_only 쿠키로 전달되므로 클라이언트가 본문에 담지 않는다.

### 3.3 응답(Response)

**성공 — 200 OK**

```json
{
  "access_token": "eyJhbGci..."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| access_token | string | 재발급된 JWT 액세스 토큰 |

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 401 | refresh 토큰 만료·무효 → 재로그인 유도 (근거: NFR-USER-001) |

---

## 4. 로그아웃 (REQ-USER-003)

### 4.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 로그아웃 API |
| 설명 | 헤더의 로그아웃 버튼으로 세션 종료, refresh 쿠키 제거 |
| 엔드포인트(Endpoint) | `/api/v1/auth/logout` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | Y |

### 4.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 액세스 토큰 |
| Cookie | refresh_token=... | http_only 쿠키 |

> 본문 없음.

### 4.3 응답(Response)

**성공 — 200 OK**

```json
{
  "message": "로그아웃 되었습니다."
}
```

- `Set-Cookie`로 refresh_token 쿠키 만료 처리.
- 클라이언트는 로그인 페이지로 전환 (근거: REQ-USER-003).

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 미인증 |

---

## 5. 회원 목록 조회 (REQ-USER-004) — 어드민

### 5.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 목록 조회 API |
| 설명 | 어드민이 전체 회원을 검색·필터하여 목록 조회 |
| 엔드포인트(Endpoint) | `/api/v1/users` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y (어드민) |

### 5.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 어드민 액세스 토큰 |

**쿼리 파라미터 (GET 요청시)**

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| search | string | N | 이메일 또는 이름 검색 (근거: REQ-USER-004) |
| department | string | N | 부서 필터 (연구/의료/개발) (근거: REQ-USER-004) |

### 5.3 응답(Response)

**성공 — 200 OK**

```json
[
  {
    "id": 1,
    "email": "user@hospital.com",
    "name": "홍길동",
    "department": "의료",
    "gender": "M",
    "phone": "010-1234-5678",
    "is_active": true
  }
]
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 고유 ID |
| email | string | 이메일 |
| name | string | 이름 |
| department | string | 부서 |
| gender | string | 성별 |
| phone | string | 휴대폰 번호 |
| is_active | boolean | 계정 활성화 여부 |

> 조회 항목은 REQ-USER-004에 명시된 7개 항목 + 고유 ID 기준.

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 미인증 |
| 403 | 어드민 권한 아님 |

---

## 6. 회원 권한 변경 (REQ-USER-005) — 어드민

### 6.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 권한 변경 API |
| 설명 | 어드민이 선택 회원의 권한 등급 변경 |
| 엔드포인트(Endpoint) | `/api/v1/users/{user_id}/role` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y (어드민) |

### 6.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 어드민 액세스 토큰 |
| Content-Type | application/json | 요청 타입 |

**본문 예시**

```json
{
  "role": "스태프"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| role | string | Y | 변경할 권한 (대기자/스태프/어드민) |

### 6.3 응답(Response)

**성공 — 200 OK**

```json
{
  "id": 5,
  "role": "스태프"
}
```

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 미인증 |
| 403 | 어드민 권한 아님 |
| 404 | 대상 회원 없음 |

---

## 7. 마이페이지 조회 (REQ-USER-006)

### 7.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 마이페이지 조회 API |
| 설명 | 로그인 유저 본인의 정보 조회 |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

### 7.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 액세스 토큰 |

### 7.3 응답(Response)

**성공 — 200 OK**

```json
{
  "name": "홍길동",
  "email": "user@hospital.com",
  "department": "의료",
  "gender": "M",
  "phone": "010-1234-5678",
  "role": "스태프"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| name | string | 이름 |
| email | string | 이메일 |
| department | string | 부서 |
| gender | string | 성별 |
| phone | string | 휴대폰 번호 |
| role | string | 권한 (대기자/스태프/어드민) |

> 조회 항목은 REQ-USER-006에 명시된 6개 항목 기준.

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 미인증 |

---

## 8. 회원 정보 수정 (REQ-USER-007)

### 8.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 정보 수정 API |
| 설명 | 본인 정보 부분 수정 (Partial Update) |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

### 8.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 액세스 토큰 |
| Content-Type | application/json | 요청 타입 |

**본문 예시**

```json
{
  "department": "연구",
  "phone": "010-9999-8888"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| department | string | N | 부서 (부분 수정) |
| phone | string | N | 휴대폰 번호 (부분 수정) |

> Partial 수정 (근거: REQ-USER-007) → 두 필드 모두 선택적. 수정 대상은 **부서·휴대폰번호에 한정**.

### 8.3 응답(Response)

**성공 — 200 OK**

```json
{
  "department": "연구",
  "phone": "010-9999-8888"
}
```

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 400 | 형식 오류 |
| 401 | 미인증 |

---

## 9. 비밀번호 변경 (REQ-USER-008)

### 9.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 비밀번호 변경 API |
| 설명 | 기존 비밀번호 검증 후 새 비밀번호 적용 |
| 엔드포인트(Endpoint) | `/api/v1/users/me/password` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

### 9.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 액세스 토큰 |
| Content-Type | application/json | 요청 타입 |

**본문 예시**

```json
{
  "current_password": "myPassword",
  "new_password": "myNewPassword"
}
```

**본문 필드**

| 파라미터명 | 타입 | 필수 (Y/N) | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 기존 비밀번호 (검증용) |
| new_password | string | Y | 새 비밀번호 |

### 9.3 응답(Response)

**성공 — 200 OK**

```json
{
  "message": "비밀번호가 변경되었습니다."
}
```

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 400 | 형식 오류 |
| 401 | 미인증 / 기존 비밀번호 불일치 |

---

## 10. 회원 탈퇴 (REQ-USER-009)

### 10.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원 탈퇴 API |
| 설명 | 본인 계정 및 관련 정보 삭제 |
| 엔드포인트(Endpoint) | `/api/v1/users/me` |
| 메서드(Method) | `DELETE` |
| 인증 필요 여부 | Y |

### 10.2 요청(Request)

**Headers**

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer &lt;access_token&gt; | 액세스 토큰 |

### 10.3 응답(Response)

**성공 — 200 OK**

```json
{
  "message": "회원 탈퇴가 완료되었습니다."
}
```

- 회원 관련 정보를 **DB에서 즉시 삭제(하드 삭제)** 한다 (근거: REQ-USER-009).
- 참고: `is_active`(계정 활성화 여부, REQ-USER-004)는 계정의 활성/비활성 상태를 나타내는 값으로, 탈퇴(완전 삭제)와는 별개 개념이다.

**실패**

| 상태 코드 | 상황 |
| --- | --- |
| 401 | 미인증 |

---

## 부록 A. 요구사항 ↔ API 매핑

| 요구사항 ID | 기능 | 엔드포인트 | 메서드 |
| --- | --- | --- | --- |
| REQ-USER-001 | 회원가입 | `/api/v1/auth/signup` | POST |
| REQ-USER-002 | 로그인 | `/api/v1/auth/login` | POST |
| NFR-USER-001 | 인증/인가 (토큰 재발급) | `/api/v1/auth/refresh` | POST |
| REQ-USER-003 | 로그아웃 | `/api/v1/auth/logout` | POST |
| REQ-USER-004 | 회원 목록 조회 | `/api/v1/users` | GET |
| REQ-USER-005 | 회원 권한 변경 | `/api/v1/users/{user_id}/role` | PATCH |
| REQ-USER-006 | 마이페이지 조회 | `/api/v1/users/me` | GET |
| REQ-USER-007 | 회원 정보 수정 | `/api/v1/users/me` | PATCH |
| REQ-USER-008 | 비밀번호 변경 | `/api/v1/users/me/password` | PATCH |
| REQ-USER-009 | 회원 탈퇴 | `/api/v1/users/me` | DELETE |

**전 API 공통 비기능 요구사항**
- NFR-USER-001: JWT 인증, Access 30분 / Refresh 7일(http_only 쿠키), 페이로드 `user_id`만.
- NFR-USER-002: 비밀번호 입력 마스킹 + 보기 토글 (프론트엔드 UI 요구사항, API 무관).
- NFR-USER-003: 모든 유저 API 3초 이내 응답.
