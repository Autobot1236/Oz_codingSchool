# 4일차 User API 설계

---

## 사용자 회원가입 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 회원가입 API |
| 설명 | 사내 의료인, 연구진, 개발자가 서비스를 이용하기 위해 회원가입하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |

#### 본문 예시

```json
{
  "email": "doctor@example.com",
  "password": "Password123!",
  "name": "홍길동",
  "department": "의료",
  "gender": "M",
  "phone_number": "010-1234-5678"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일 |
| password | string | Y | 사용자 비밀번호 |
| name | string | Y | 사용자 이름 |
| department | string | Y | 부서. 연구, 의료, 개발 중 하나 |
| gender | string | Y | 성별. M 또는 F |
| phone_number | string | Y | 사용자 휴대폰 번호 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | POST 요청이므로 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 201 Created

```json
{
  "id": 1,
  "email": "doctor@example.com",
  "name": "홍길동",
  "department": "의료",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "pending",
  "is_active": true
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 생성된 사용자 ID |
| email | string | 사용자 이메일 |
| name | string | 사용자 이름 |
| department | string | 사용자 부서 |
| gender | string | 사용자 성별 |
| phone_number | string | 사용자 휴대폰 번호 |
| role | string | 사용자 권한. 기본값 pending |
| is_active | boolean | 계정 활성화 여부 |

#### 실패

- 400 Bad Request

```json
{
  "detail": "이미 존재하는 이메일입니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 이메일 중복 또는 잘못된 요청에 대한 에러 메시지 |

---

### 4. 비고

- 비밀번호는 응답에 포함하지 않습니다.
- 비밀번호는 평문이 아닌 암호화된 형태로 저장되어야 합니다.
- 회원가입 직후 기본 권한은 대기자 상태인 `pending`으로 설정합니다.

---

## 사용자 로그인 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 로그인 API |
| 설명 | 이메일과 비밀번호를 입력하여 로그인하고 JWT 토큰을 발급받는 API |
| 엔드포인트(Endpoint) | `/api/v1/auth/login/` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | N |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |

#### 본문 예시

```json
{
  "email": "doctor@example.com",
  "password": "Password123!"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| email | string | Y | 사용자 이메일 |
| password | string | Y | 사용자 비밀번호 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | POST 요청이므로 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "doctor@example.com",
    "name": "홍길동",
    "role": "staff"
  }
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| access_token | string | JWT 액세스 토큰 |
| token_type | string | 토큰 타입 |
| user | object | 로그인한 사용자 정보 |

#### 실패

- 400 Bad Request

```json
{
  "detail": "이메일 또는 비밀번호가 일치하지 않습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 로그인 실패 에러 메시지 |

---

### 4. 비고

- 로그인 성공 시 액세스 토큰을 발급합니다.
- 리프레시 토큰은 클라이언트에서 접근할 수 없도록 http_only 쿠키로 전달합니다.
- JWT payload에는 최소 식별 정보인 `user_id`만 저장합니다.
- 액세스 토큰 만료 주기는 30분, 리프레시 토큰 만료 주기는 7일로 설정합니다.

---

## 사용자 로그아웃 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 로그아웃 API |
| 설명 | 로그인한 사용자가 로그아웃하는 API |
| 엔드포인트(Endpoint) | `/api/v1/auth/logout/` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 요청 본문을 사용하지 않음 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | POST 요청이므로 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "message": "로그아웃되었습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| message | string | 로그아웃 성공 메시지 |

#### 실패

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 인증 실패에 대한 에러 메시지 |

---

### 4. 비고

- 로그아웃 후 클라이언트는 로그인 페이지로 이동합니다.
- 서버는 리프레시 토큰 쿠키를 만료 처리합니다.

---

## 사용자 목록 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 목록 조회 API |
| 설명 | 관리자 권한 사용자가 모든 회원 목록을 조회하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | GET 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| keyword | string | N | 이메일 또는 이름 검색어 |
| department | string | N | 부서 필터. 연구, 의료, 개발 중 하나 |
| page | integer | N | 조회할 페이지 번호 |
| size | integer | N | 한 페이지에 조회할 사용자 수 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "users": [
    {
      "id": 1,
      "email": "doctor@example.com",
      "name": "홍길동",
      "department": "의료",
      "gender": "M",
      "phone_number": "010-1234-5678",
      "role": "staff",
      "is_active": true
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| users | array | 사용자 목록 |
| page | integer | 현재 페이지 번호 |
| size | integer | 한 페이지에 조회할 사용자 수 |
| total | integer | 전체 사용자 수 |

#### 실패

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 인증 실패에 대한 에러 메시지 |

- 403 Forbidden

```json
{
  "detail": "관리자 권한이 필요합니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 관리자 권한이 없는 경우의 에러 메시지 |

---

### 4. 비고

- 관리자 권한인 `admin` 사용자만 회원 목록을 조회할 수 있습니다.
- 이메일 또는 이름으로 검색할 수 있습니다.
- 부서 드롭다운 필터를 통해 연구, 의료, 개발 부서별 조회가 가능합니다.

---

## 사용자 권한 변경 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 권한 변경 API |
| 설명 | 관리자 권한 사용자가 특정 사용자의 권한을 변경하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/{user_id}/role/` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{
  "role": "staff"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| role | string | Y | 변경할 권한. pending, staff, admin 중 하나 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| user_id | integer | Y | 권한을 변경할 사용자 ID |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | PATCH 요청이므로 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "id": 1,
  "email": "doctor@example.com",
  "name": "홍길동",
  "role": "staff"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 사용자 ID |
| email | string | 사용자 이메일 |
| name | string | 사용자 이름 |
| role | string | 변경된 사용자 권한 |

#### 실패

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

- 403 Forbidden

```json
{
  "detail": "관리자 권한이 필요합니다."
}
```

- 404 Not Found

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

---

### 4. 비고

- 권한은 `pending`, `staff`, `admin` 중 하나로 변경할 수 있습니다.
- `pending` 사용자는 마이페이지 외 모든 서비스에 접근할 수 없습니다.
- `staff` 사용자는 흉부 X-ray 관련 읽기, 쓰기, 수정 작업이 가능합니다.
- `admin` 사용자는 시스템 관리자 권한을 가집니다.

---

## 마이페이지 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 마이페이지 조회 API |
| 설명 | 로그인한 사용자가 본인의 정보를 조회하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/me/` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | GET 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "id": 1,
  "email": "doctor@example.com",
  "name": "홍길동",
  "department": "의료",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "role": "staff"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 사용자 ID |
| email | string | 사용자 이메일 |
| name | string | 사용자 이름 |
| department | string | 사용자 부서 |
| gender | string | 사용자 성별 |
| phone_number | string | 사용자 휴대폰 번호 |
| role | string | 사용자 권한 |

#### 실패

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 인증 실패에 대한 에러 메시지 |

---

### 4. 비고

- 모든 로그인 사용자가 본인의 정보를 조회할 수 있습니다.
- 비밀번호는 응답에 포함하지 않습니다.

---

## 회원정보 수정 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원정보 수정 API |
| 설명 | 로그인한 사용자가 본인의 부서와 휴대폰 번호를 수정하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/me/` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{
  "department": "연구",
  "phone_number": "010-9876-5432"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| department | string | N | 변경할 부서. 연구, 의료, 개발 중 하나 |
| phone_number | string | N | 변경할 휴대폰 번호 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | PATCH 요청이므로 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "id": 1,
  "email": "doctor@example.com",
  "name": "홍길동",
  "department": "연구",
  "gender": "M",
  "phone_number": "010-9876-5432",
  "role": "staff"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 사용자 ID |
| email | string | 사용자 이메일 |
| name | string | 사용자 이름 |
| department | string | 사용자 부서 |
| gender | string | 사용자 성별 |
| phone_number | string | 사용자 휴대폰 번호 |
| role | string | 사용자 권한 |

#### 실패

- 400 Bad Request

```json
{
  "detail": "수정할 필드가 없습니다."
}
```

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

---

### 4. 비고

- 회원정보 수정은 부분 수정 방식으로 처리합니다.
- 수정 가능한 항목은 부서와 휴대폰 번호입니다.

---

## 비밀번호 변경 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 비밀번호 변경 API |
| 설명 | 로그인한 사용자가 기존 비밀번호 검증 후 새 비밀번호로 변경하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/me/password/` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Content-Type | application/json | 요청 타입 |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{
  "current_password": "Password123!",
  "new_password": "NewPassword123!"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| current_password | string | Y | 기존 비밀번호 |
| new_password | string | Y | 새로운 비밀번호 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | PATCH 요청이므로 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "message": "비밀번호가 변경되었습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| message | string | 비밀번호 변경 성공 메시지 |

#### 실패

- 400 Bad Request

```json
{
  "detail": "기존 비밀번호가 일치하지 않습니다."
}
```

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

---

### 4. 비고

- 기존 비밀번호가 일치하는지 검증한 후 새 비밀번호를 적용합니다.
- 새 비밀번호는 암호화하여 저장합니다.
- 비밀번호 입력 UI는 마스킹 처리하며, 보기 아이콘으로 입력값 확인이 가능해야 합니다.

---

## 회원탈퇴 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 회원탈퇴 API |
| 설명 | 로그인한 사용자가 본인 계정을 탈퇴하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/me/` |
| 메서드(Method) | `DELETE` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer <access_token> | 인증 토큰 |

#### 본문 예시

```json
{}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | DELETE 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터 (GET 요청시)

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 204 No Content

```json
{}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| 없음 | - | 탈퇴 성공 시 응답 본문 없음 |

#### 실패

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

---

### 4. 비고

- 회원탈퇴 시 데이터베이스에서 회원과 관련된 정보를 즉시 삭제합니다.
- 탈퇴 후 해당 계정으로는 서비스를 이용할 수 없습니다.

---

## 공통 비기능 요구사항

| 항목 | 내용 |
| --- | --- |
| 인증/인가 | 로그인 성공 시 JWT를 발급하고, 인증이 필요한 API는 Authorization 헤더를 사용합니다. |
| 액세스 토큰 만료 | 액세스 토큰 만료 주기는 30분입니다. |
| 리프레시 토큰 만료 | 리프레시 토큰 만료 주기는 7일입니다. |
| 리프레시 토큰 전달 방식 | 리프레시 토큰은 http_only 쿠키로 전달합니다. |
| JWT Payload | JWT payload에는 최소 식별 정보인 `user_id`만 저장합니다. |
| 비밀번호 입력 보안 | 모든 비밀번호 입력은 마스킹 처리하고 보기 아이콘으로 확인할 수 있게 합니다. |
| API 성능 | 모든 User API는 최대 3초 이내에 응답하도록 합니다. |