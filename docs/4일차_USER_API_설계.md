# 흉부 X-Ray AI 진단 서비스 사용자 API 명세서

## 1. 공통 사항

### 1.1 기본 정보

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 데이터 형식 | `application/json` |
| 문자 인코딩 | UTF-8 |
| 인증 방식 | JWT Bearer Token |
| Access Token 유효기간 | 30분 |
| Refresh Token 유효기간 | 7일 |
| 날짜 형식 | ISO 8601 UTC (`2026-07-20T10:30:00Z`) |
| API 응답 제한시간 | 최대 3초 |

### 1.2 권한

| 권한 | 코드 | 접근 범위 |
| --- | --- | --- |
| 대기자 | `PENDING` | 마이페이지 관련 API만 사용 가능 |
| 스태프 | `STAFF` | 흉부 X-Ray 관련 읽기·쓰기·수정 가능 |
| 관리자 | `ADMIN` | 전체 데이터 및 회원관리 기능 접근 가능 |

회원가입 직후 기본 권한은 `PENDING`으로 지정한다.

### 1.3 인증 헤더

Access Token이 필요한 API는 다음 헤더를 사용한다.

```http
Authorization: Bearer {access_token}
```

Refresh Token은 JavaScript에서 접근할 수 없는 `HttpOnly` 쿠키로 전달한다.

```http
Set-Cookie: refresh_token={token}; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth
```

### 1.4 공통 성공 응답

```json
{
  "success": true,
  "data": {},
  "message": "요청이 정상적으로 처리되었습니다."
}
```

데이터가 없는 성공 응답은 HTTP `204 No Content`를 사용하며 응답 본문을 반환하지 않는다.

### 1.5 공통 오류 응답

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "fields": [
      {
        "field": "email",
        "reason": "올바른 이메일 형식이 아닙니다."
      }
    ]
  }
}
```

### 1.6 공통 HTTP 상태 코드

| 상태 코드 | 의미 |
| --- | --- |
| `200 OK` | 조회·수정 성공 |
| `201 Created` | 리소스 생성 성공 |
| `204 No Content` | 응답 데이터가 없는 성공 |
| `400 Bad Request` | 형식 오류 또는 유효하지 않은 요청 |
| `401 Unauthorized` | 인증 실패 또는 만료된 토큰 |
| `403 Forbidden` | 접근 권한 부족 |
| `404 Not Found` | 대상 리소스 없음 |
| `409 Conflict` | 이메일 중복 등 데이터 충돌 |
| `422 Unprocessable Entity` | 비밀번호 불일치 등 업무 규칙 위반 |
| `500 Internal Server Error` | 서버 내부 오류 |
| `503 Service Unavailable` | 일시적인 서비스 장애 |

---

## 2. 공통 데이터 모델

### 2.1 사용자

```json
{
  "id": 1001,
  "email": "doctor@example.com",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phoneNumber": "01012345678",
  "role": "STAFF",
  "active": true,
  "createdAt": "2026-07-20T10:30:00Z",
  "updatedAt": "2026-07-20T10:30:00Z"
}
```

### 2.2 열거형

#### 부서 `department`

| 값 | 의미 |
| --- | --- |
| `RESEARCH` | 연구 |
| `MEDICAL` | 의료 |
| `DEVELOPMENT` | 개발 |

#### 성별 `gender`

| 값 | 의미 |
| --- | --- |
| `M` | 남성 |
| `F` | 여성 |

#### 권한 `role`

| 값 | 의미 |
| --- | --- |
| `PENDING` | 대기자 |
| `STAFF` | 스태프 |
| `ADMIN` | 관리자 |

### 2.3 입력값 검증 기준

| 필드 | 검증 기준 |
| --- | --- |
| `email` | 필수, 유효한 이메일 형식, 최대 254자, 시스템 내 고유값 |
| `password` | 필수, 8~64자, 영문·숫자·특수문자 각각 1개 이상 포함 |
| `name` | 필수, 공백 제거 후 2~50자 |
| `department` | `RESEARCH`, `MEDICAL`, `DEVELOPMENT` 중 하나 |
| `gender` | `M`, `F` 중 하나 |
| `phoneNumber` | 숫자만 입력, 10~11자리 |
| `role` | `PENDING`, `STAFF`, `ADMIN` 중 하나 |

비밀번호는 응답, 로그 및 JWT 페이로드에 포함하지 않는다. 서버 저장 시 단방향 해시를 적용한다.

---

# 3. 인증 API

## 3.1 회원가입

- 요구사항: `REQ-USER-001`
- Method: `POST`
- URL: `/users`
- 인증: 불필요

### 요청

```json
{
  "email": "doctor@example.com",
  "password": "Secure!234",
  "name": "홍길동",
  "department": "MEDICAL",
  "gender": "M",
  "phoneNumber": "01012345678"
}
```

### 성공 응답: `201 Created`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "email": "doctor@example.com",
    "name": "홍길동",
    "department": "MEDICAL",
    "gender": "M",
    "phoneNumber": "01012345678",
    "role": "PENDING",
    "active": true,
    "createdAt": "2026-07-20T10:30:00Z"
  },
  "message": "회원가입이 완료되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `VALIDATION_ERROR` | 필수값 누락 또는 입력 형식 오류 |
| `409` | `EMAIL_ALREADY_EXISTS` | 이미 가입된 이메일 |
| `409` | `PHONE_NUMBER_ALREADY_EXISTS` | 휴대폰 번호를 고유값으로 관리하는 경우 중복 발생 |

---

## 3.2 로그인

- 요구사항: `REQ-USER-002`, `NFR-USER-001`
- Method: `POST`
- URL: `/auth/login`
- 인증: 불필요

### 요청

```json
{
  "email": "doctor@example.com",
  "password": "Secure!234"
}
```

### 성공 응답: `200 OK`

응답 본문으로 Access Token을 반환하고, Refresh Token은 `HttpOnly` 쿠키로 설정한다.

```http
Set-Cookie: refresh_token={refresh_token}; Max-Age=604800; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth
```

```json
{
  "success": true,
  "data": {
    "accessToken": "{access_token}",
    "tokenType": "Bearer",
    "expiresIn": 1800,
    "user": {
      "id": 1001,
      "name": "홍길동",
      "role": "STAFF"
    }
  },
  "message": "로그인되었습니다."
}
```

JWT 페이로드에는 최소 식별 정보만 저장한다.

```json
{
  "user_id": 1001,
  "iat": 1784539800,
  "exp": 1784541600
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `VALIDATION_ERROR` | 이메일 또는 비밀번호 누락 |
| `401` | `INVALID_CREDENTIALS` | 이메일 또는 비밀번호 불일치 |
| `403` | `ACCOUNT_INACTIVE` | 비활성 계정 |

보안을 위해 이메일 존재 여부와 비밀번호 오류를 구분하지 않고 동일한 인증 실패 메시지를 반환한다.

---

## 3.3 Access Token 재발급

- 요구사항: `NFR-USER-001`
- Method: `POST`
- URL: `/auth/refresh`
- 인증: Refresh Token 쿠키 필요

### 요청

요청 본문은 없으며 브라우저가 `refresh_token` 쿠키를 자동 전송한다.

```http
Cookie: refresh_token={refresh_token}
```

### 성공 응답: `200 OK`

Refresh Token Rotation을 적용하여 새 Refresh Token도 쿠키로 전달한다.

```json
{
  "success": true,
  "data": {
    "accessToken": "{new_access_token}",
    "tokenType": "Bearer",
    "expiresIn": 1800
  },
  "message": "Access Token이 재발급되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `401` | `REFRESH_TOKEN_MISSING` | 쿠키에 Refresh Token이 없음 |
| `401` | `REFRESH_TOKEN_INVALID` | 변조되거나 폐기된 토큰 |
| `401` | `REFRESH_TOKEN_EXPIRED` | Refresh Token 만료 |

Refresh Token 만료 시 클라이언트는 저장된 인증 상태를 제거하고 로그인 페이지로 이동한다.

---

## 3.4 로그아웃

- 요구사항: `REQ-USER-003`
- Method: `POST`
- URL: `/auth/logout`
- 인증: Access Token 필요
- 쿠키: Refresh Token

### 처리

서버에 저장된 Refresh Token 또는 토큰 식별자를 폐기하고 쿠키를 삭제한다.

```http
Set-Cookie: refresh_token=; Max-Age=0; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth
```

### 성공 응답: `204 No Content`

클라이언트는 Access Token을 제거하고 로그인 페이지로 이동한다.

### 오류

로그아웃은 멱등성을 보장한다. 이미 로그아웃되었거나 Refresh Token이 없어도 `204`를 반환할 수 있다.

---

# 4. 마이페이지 API

## 4.1 내 정보 조회

- 요구사항: `REQ-USER-006`
- Method: `GET`
- URL: `/users/me`
- 인증: Access Token 필요
- 권한: `PENDING`, `STAFF`, `ADMIN`

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "name": "홍길동",
    "email": "doctor@example.com",
    "department": "MEDICAL",
    "gender": "M",
    "phoneNumber": "01012345678",
    "role": "STAFF"
  },
  "message": "회원 정보를 조회했습니다."
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `401` | `ACCESS_TOKEN_INVALID` | Access Token이 없거나 유효하지 않음 |
| `401` | `ACCESS_TOKEN_EXPIRED` | Access Token 만료 |
| `404` | `USER_NOT_FOUND` | 토큰의 사용자 계정이 존재하지 않음 |

---

## 4.2 내 정보 부분 수정

- 요구사항: `REQ-USER-007`
- Method: `PATCH`
- URL: `/users/me`
- 인증: Access Token 필요
- 권한: `PENDING`, `STAFF`, `ADMIN`

`department`와 `phoneNumber` 중 하나 이상을 전달한다. 전달하지 않은 항목은 기존 값을 유지한다.

### 요청 예시 1

```json
{
  "department": "RESEARCH"
}
```

### 요청 예시 2

```json
{
  "phoneNumber": "01098765432"
}
```

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "name": "홍길동",
    "email": "doctor@example.com",
    "department": "RESEARCH",
    "gender": "M",
    "phoneNumber": "01098765432",
    "role": "STAFF",
    "updatedAt": "2026-07-20T11:00:00Z"
  },
  "message": "회원 정보가 수정되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `EMPTY_UPDATE_REQUEST` | 수정할 필드가 없음 |
| `400` | `VALIDATION_ERROR` | 부서 또는 휴대폰 번호 형식 오류 |
| `400` | `UNSUPPORTED_FIELD` | 수정할 수 없는 필드 전달 |
| `409` | `PHONE_NUMBER_ALREADY_EXISTS` | 휴대폰 번호 중복 정책을 적용한 경우 |

---

## 4.3 비밀번호 변경

- 요구사항: `REQ-USER-008`
- Method: `PUT`
- URL: `/users/me/password`
- 인증: Access Token 필요
- 권한: `PENDING`, `STAFF`, `ADMIN`

### 요청

```json
{
  "currentPassword": "Secure!234",
  "newPassword": "NewSecure!567"
}
```

### 성공 응답: `204 No Content`

비밀번호 변경 후 기존 Refresh Token을 모두 폐기한다. 클라이언트는 로그인 페이지로 이동하여 변경된 비밀번호로 다시 로그인하도록 유도한다.

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `VALIDATION_ERROR` | 새 비밀번호가 보안 규칙을 충족하지 않음 |
| `422` | `CURRENT_PASSWORD_MISMATCH` | 기존 비밀번호 불일치 |
| `422` | `PASSWORD_REUSE_NOT_ALLOWED` | 새 비밀번호가 기존 비밀번호와 같음 |

---

## 4.4 회원 탈퇴

- 요구사항: `REQ-USER-009`
- Method: `DELETE`
- URL: `/users/me`
- 인증: Access Token 필요
- 권한: `PENDING`, `STAFF`, `ADMIN`

### 요청

실수로 인한 탈퇴를 줄이기 위해 현재 비밀번호를 다시 검증한다.

```json
{
  "password": "Secure!234"
}
```

### 성공 응답: `204 No Content`

처리 사항:

1. 회원과 직접 연관된 정보를 트랜잭션으로 즉시 삭제한다.
2. 사용자의 모든 Refresh Token을 폐기한다.
3. Refresh Token 쿠키를 삭제한다.
4. 클라이언트는 Access Token을 제거하고 로그인 페이지로 이동한다.

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `401` | `ACCESS_TOKEN_INVALID` | 인증 실패 |
| `422` | `PASSWORD_MISMATCH` | 비밀번호 불일치 |
| `404` | `USER_NOT_FOUND` | 회원이 이미 삭제됨 |
| `409` | `USER_DELETE_CONFLICT` | 연관 데이터 처리 실패 |

의료·진단 데이터에 법적 보존 의무가 있는 경우 회원 식별정보 삭제와 진단 기록 보존 정책을 별도로 정의해야 한다.

---

# 5. 관리자 회원관리 API

## 5.1 회원 목록 조회

- 요구사항: `REQ-USER-004`
- Method: `GET`
- URL: `/admin/users`
- 인증: Access Token 필요
- 권한: `ADMIN`

### Query Parameters

| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `keyword` | string | 아니요 | - | 이메일 또는 이름 부분 일치 검색 |
| `department` | enum | 아니요 | - | 부서 필터 |
| `role` | enum | 아니요 | - | 권한 필터 |
| `active` | boolean | 아니요 | - | 계정 활성화 여부 |
| `page` | integer | 아니요 | `0` | 페이지 번호, 0부터 시작 |
| `size` | integer | 아니요 | `20` | 페이지당 항목 수, 최대 100 |
| `sort` | string | 아니요 | `createdAt,desc` | `{필드},{asc\|desc}` |

### 요청 예시

```http
GET /api/v1/admin/users?keyword=홍길동&department=MEDICAL&page=0&size=20&sort=createdAt,desc
```

`keyword`가 이메일 형식이면 이메일을 우선 검색하지 않고, 이름과 이메일에 대해 동일한 부분 일치 조건을 적용한다.

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 1001,
        "email": "doctor@example.com",
        "name": "홍길동",
        "department": "MEDICAL",
        "gender": "M",
        "phoneNumber": "01012345678",
        "role": "STAFF",
        "active": true
      }
    ],
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1,
    "first": true,
    "last": true
  },
  "message": "회원 목록을 조회했습니다."
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `INVALID_QUERY_PARAMETER` | 잘못된 필터, 정렬 또는 페이지 값 |
| `401` | `ACCESS_TOKEN_INVALID` | 인증 실패 |
| `403` | `ADMIN_PERMISSION_REQUIRED` | 관리자 권한 없음 |

---

## 5.2 회원 권한 변경

- 요구사항: `REQ-USER-005`
- Method: `PATCH`
- URL: `/admin/users/{userId}/role`
- 인증: Access Token 필요
- 권한: `ADMIN`

### Path Parameter

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `userId` | integer | 권한을 변경할 회원의 고유 ID |

### 요청

```json
{
  "role": "STAFF"
}
```

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "email": "doctor@example.com",
    "name": "홍길동",
    "role": "STAFF",
    "updatedAt": "2026-07-20T11:30:00Z"
  },
  "message": "회원 권한이 변경되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `INVALID_ROLE` | 지원하지 않는 권한 |
| `403` | `ADMIN_PERMISSION_REQUIRED` | 관리자 권한 없음 |
| `404` | `USER_NOT_FOUND` | 변경 대상 회원 없음 |
| `409` | `LAST_ADMIN_ROLE_CHANGE_DENIED` | 마지막 활성 관리자의 권한을 하향하려는 경우 |
| `409` | `INACTIVE_USER_ROLE_CHANGE_DENIED` | 비활성 회원의 권한 변경 시도 |

대상 회원의 권한이 변경되면 기존 Access Token의 권한 캐시를 사용하지 않는다. 각 요청에서 DB 권한을 확인하거나 권한 변경 시 해당 사용자의 토큰을 폐기한다.

---

## 5.3 회원 권한 일괄 변경

요구사항의 “목록에서 대상자를 선택”하는 동작이 다중 선택을 포함할 수 있으므로 일괄 변경 API를 추가로 정의한다.

- 요구사항: `REQ-USER-005`
- Method: `PATCH`
- URL: `/admin/users/roles`
- 인증: Access Token 필요
- 권한: `ADMIN`

### 요청

```json
{
  "userIds": [1001, 1002, 1003],
  "role": "STAFF"
}
```

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "requestedCount": 3,
    "updatedCount": 3,
    "failedCount": 0,
    "results": [
      {
        "userId": 1001,
        "updated": true
      },
      {
        "userId": 1002,
        "updated": true
      },
      {
        "userId": 1003,
        "updated": true
      }
    ]
  },
  "message": "선택한 회원의 권한이 변경되었습니다."
}
```

일괄 변경은 전체 성공 또는 전체 실패 방식의 트랜잭션 처리를 기본으로 한다.

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `400` | `EMPTY_USER_SELECTION` | 선택된 회원 없음 |
| `400` | `TOO_MANY_USERS_SELECTED` | 한 번에 100명을 초과하여 선택 |
| `404` | `USER_NOT_FOUND` | 대상 중 존재하지 않는 회원이 있음 |
| `409` | `LAST_ADMIN_ROLE_CHANGE_DENIED` | 마지막 관리자의 권한 하향 포함 |

---

## 5.4 회원 활성화 상태 변경

회원 목록에서 활성화 여부를 조회하지만 기존 요구사항에는 상태 변경 기능이 명시되지 않았다. 관리 기능 확장을 고려하여 선택 API로 정의한다.

- Method: `PATCH`
- URL: `/admin/users/{userId}/active`
- 인증: Access Token 필요
- 권한: `ADMIN`

### 요청

```json
{
  "active": false
}
```

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "active": false,
    "updatedAt": "2026-07-20T12:00:00Z"
  },
  "message": "계정 상태가 변경되었습니다."
}
```

비활성화 시 해당 회원의 Refresh Token을 모두 폐기한다.

### 오류

| 상태 | 오류 코드 | 발생 조건 |
| --- | --- | --- |
| `403` | `ADMIN_PERMISSION_REQUIRED` | 관리자 권한 없음 |
| `404` | `USER_NOT_FOUND` | 대상 회원 없음 |
| `409` | `LAST_ADMIN_DEACTIVATION_DENIED` | 마지막 활성 관리자 비활성화 시도 |
| `409` | `SELF_DEACTIVATION_DENIED` | 관리자가 자기 계정을 비활성화하려는 경우 |

---

# 6. 오류 코드 목록

| 오류 코드 | HTTP | 설명 |
| --- | --- | --- |
| `VALIDATION_ERROR` | `400` | 입력값 검증 실패 |
| `EMPTY_UPDATE_REQUEST` | `400` | 수정할 항목 없음 |
| `UNSUPPORTED_FIELD` | `400` | 수정 불가능한 필드 전달 |
| `INVALID_QUERY_PARAMETER` | `400` | 조회 조건 오류 |
| `INVALID_ROLE` | `400` | 지원하지 않는 권한 |
| `EMPTY_USER_SELECTION` | `400` | 선택된 회원 없음 |
| `TOO_MANY_USERS_SELECTED` | `400` | 일괄 처리 허용 건수 초과 |
| `ACCESS_TOKEN_INVALID` | `401` | 유효하지 않은 Access Token |
| `ACCESS_TOKEN_EXPIRED` | `401` | 만료된 Access Token |
| `REFRESH_TOKEN_MISSING` | `401` | Refresh Token 없음 |
| `REFRESH_TOKEN_INVALID` | `401` | 유효하지 않은 Refresh Token |
| `REFRESH_TOKEN_EXPIRED` | `401` | 만료된 Refresh Token |
| `INVALID_CREDENTIALS` | `401` | 로그인 정보 불일치 |
| `ADMIN_PERMISSION_REQUIRED` | `403` | 관리자 권한 필요 |
| `ACCOUNT_INACTIVE` | `403` | 비활성 계정 |
| `USER_NOT_FOUND` | `404` | 회원을 찾을 수 없음 |
| `EMAIL_ALREADY_EXISTS` | `409` | 이메일 중복 |
| `PHONE_NUMBER_ALREADY_EXISTS` | `409` | 휴대폰 번호 중복 |
| `LAST_ADMIN_ROLE_CHANGE_DENIED` | `409` | 마지막 관리자 권한 하향 불가 |
| `LAST_ADMIN_DEACTIVATION_DENIED` | `409` | 마지막 관리자 비활성화 불가 |
| `SELF_DEACTIVATION_DENIED` | `409` | 자기 계정 비활성화 불가 |
| `CURRENT_PASSWORD_MISMATCH` | `422` | 기존 비밀번호 불일치 |
| `PASSWORD_REUSE_NOT_ALLOWED` | `422` | 기존 비밀번호 재사용 |
| `INTERNAL_SERVER_ERROR` | `500` | 서버 내부 오류 |

---

# 7. 보안 및 구현 정책

## 7.1 비밀번호

- 모든 비밀번호 입력란은 기본적으로 마스킹한다.
- 비밀번호 보기 버튼을 제공한다.
- 서버는 비밀번호 원문을 저장하거나 기록하지 않는다.
- Argon2id 또는 bcrypt와 같은 검증된 단방향 해시를 사용한다.
- 로그인 실패 횟수 제한 및 일정 시간 잠금 정책 적용을 권장한다.

## 7.2 JWT 및 Refresh Token

- JWT 서명 알고리즘과 비밀키는 서버 환경설정으로 관리한다.
- JWT 페이로드에는 `user_id`, `iat`, `exp`만 포함한다.
- Refresh Token은 원문 대신 해시값 또는 토큰 식별자를 서버에 저장한다.
- 로그아웃, 비밀번호 변경, 회원 탈퇴 및 계정 비활성화 시 Refresh Token을 폐기한다.
- Refresh Token Rotation과 재사용 탐지를 적용한다.
- 쿠키 인증 요청에 대비해 `SameSite` 설정과 CSRF 방어를 적용한다.

## 7.3 개인정보

- 전화번호, 이메일 등의 개인정보를 애플리케이션 로그에 원문으로 기록하지 않는다.
- 관리자 API 접근 및 권한 변경 이력은 감사 로그로 남긴다.
- 회원 탈퇴 시 삭제되는 데이터의 범위와 법적 보존 대상 데이터를 구분한다.

## 7.4 API 성능

모든 사용자 API는 정상 운영 조건에서 서버 처리시간 3초 이내를 만족해야 한다.

- 목록 조회에는 페이지네이션을 필수 적용한다.
- 이메일에는 고유 인덱스를 적용한다.
- 이름, 부서, 권한, 활성 상태 등 검색·필터 필드에 적절한 인덱스를 검토한다.
- 외부 연동으로 인해 3초를 초과하지 않도록 타임아웃을 설정한다.

---

# 8. 요구사항 추적표

| 요구사항 ID | API |
| --- | --- |
| `REQ-USER-001` | `POST /users` |
| `REQ-USER-002` | `POST /auth/login` |
| `NFR-USER-001` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` |
| `REQ-USER-003` | `POST /auth/logout` |
| `REQ-USER-004` | `GET /admin/users` |
| `REQ-USER-005` | `PATCH /admin/users/{userId}/role`, `PATCH /admin/users/roles` |
| `REQ-USER-006` | `GET /users/me` |
| `REQ-USER-007` | `PATCH /users/me` |
| `REQ-USER-008` | `PUT /users/me/password` |
| `REQ-USER-009` | `DELETE /users/me` |
| `NFR-USER-002` | 프론트엔드 비밀번호 입력 컴포넌트 |
| `NFR-USER-003` | 모든 사용자 API |

---

# 9. 확정이 필요한 정책

다음 항목은 원본 요구사항에 명시되지 않아 본 명세에서 권장값을 적용했다.

1. 회원가입 직후 기본 권한은 `PENDING`으로 가정했다.
2. `active`는 권한과 별개의 계정 상태로 정의했다.
3. 비밀번호는 8~64자이며 영문·숫자·특수문자를 포함하도록 정의했다.
4. 휴대폰 번호는 하이픈 없이 10~11자리 숫자로 정의했다.
5. 휴대폰 번호의 중복 허용 여부는 최종 확정이 필요하다.
6. 회원 탈퇴 시 안전을 위해 현재 비밀번호 재입력을 추가했다.
7. 비밀번호 변경 후 모든 세션을 종료하도록 정의했다.
8. 관리자 목록은 0부터 시작하는 페이지 방식으로 정의했다.
9. 회원 권한 변경 대상의 다중 선택 가능성을 고려해 일괄 API를 추가했다.
10. 계정 활성화 상태 변경 API는 원본 요구사항에 없는 선택 기능이다.
11. 마지막 관리자 보호 정책을 적용했다.
12. 회원 탈퇴 시 진단 기록 등 법적 보존 데이터의 처리 정책은 별도 확정이 필요하다.
