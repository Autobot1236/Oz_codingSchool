# 4일차 User API 설계

---

## 사용자 회원가입 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 회원가입 API |
| 설명 | 이름, 이메일, 비밀번호, 나이를 입력받아 새 사용자를 생성하는 API |
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
  "name": "홍길동",
  "email": "gildong@example.com",
  "password": "Password123!",
  "age": 24
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 사용자 이름 |
| email | string | Y | 사용자 이메일 |
| password | string | Y | 사용자 비밀번호 |
| age | integer | Y | 사용자 나이 |

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
  "name": "홍길동",
  "email": "gildong@example.com",
  "age": 24
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 생성된 사용자 ID |
| name | string | 사용자 이름 |
| email | string | 사용자 이메일 |
| age | integer | 사용자 나이 |

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
- 비밀번호는 실제 서비스에서는 평문이 아닌 암호화된 형태로 저장되어야 합니다.
- 이메일은 중복 가입을 허용하지 않습니다.

# 4일차 User API 설계


---

## 사용자 목록 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 목록 조회 API |
| 설명 | 등록된 사용자 목록을 페이지 단위로 조회하는 API |
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
| page | integer | N | 조회할 페이지 번호 |
| size | integer | N | 한 페이지에 조회할 사용자 수 |
| keyword | string | N | 사용자 이름 또는 이메일 검색어 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "users": [
    {
      "id": 1,
      "name": "홍길동",
      "email": "gildong@example.com",
      "age": 24
    },
    {
      "id": 2,
      "name": "김철수",
      "email": "chulsoo@example.com",
      "age": 28
    }
  ],
  "page": 1,
  "size": 10,
  "total": 2
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

---

### 4. 비고

- 인증된 사용자만 목록을 조회할 수 있습니다.
- `page`와 `size`를 사용하여 페이지네이션을 처리합니다.
- `keyword`를 사용하여 이름 또는 이메일 기준으로 검색할 수 있습니다.

---

## 사용자 상세 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 상세 조회 API |
| 설명 | 사용자 ID를 이용하여 특정 사용자의 상세 정보를 조회하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/{user_id}/` |
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

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| user_id | integer | Y | 조회할 사용자 ID |

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
  "name": "홍길동",
  "email": "gildong@example.com",
  "age": 24
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 사용자 ID |
| name | string | 사용자 이름 |
| email | string | 사용자 이메일 |
| age | integer | 사용자 나이 |

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

- 404 Not Found

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 존재하지 않는 사용자 ID로 요청한 경우의 에러 메시지 |

---

### 4. 비고

- 인증된 사용자만 상세 정보를 조회할 수 있습니다.
- `user_id`는 URL 경로에 포함됩니다.
- 비밀번호는 응답에 포함하지 않습니다.

---

## 사용자 정보 수정 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 정보 수정 API |
| 설명 | 사용자 ID를 이용하여 특정 사용자의 정보를 수정하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/{user_id}/` |
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
  "name": "홍길동",
  "password": "NewPassword123!",
  "age": 25
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| name | string | N | 변경할 사용자 이름 |
| password | string | N | 변경할 사용자 비밀번호 |
| age | integer | N | 변경할 사용자 나이 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| user_id | integer | Y | 수정할 사용자 ID |

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
  "name": "홍길동",
  "email": "gildong@example.com",
  "age": 25
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 사용자 ID |
| name | string | 사용자 이름 |
| email | string | 사용자 이메일 |
| age | integer | 사용자 나이 |

#### 실패

- 400 Bad Request

```json
{
  "detail": "수정할 필드가 없습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 수정할 데이터가 없는 경우의 에러 메시지 |

- 401 Unauthorized

```json
{
  "detail": "인증 정보가 유효하지 않습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 인증 실패에 대한 에러 메시지 |

- 404 Not Found

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 존재하지 않는 사용자 ID로 요청한 경우의 에러 메시지 |

---

### 4. 비고

- 요청 본문에는 수정할 필드만 포함할 수 있습니다.
- 비밀번호를 수정하는 경우 실제 서비스에서는 암호화 후 저장해야 합니다.
- 이메일은 사용자 식별 정보이므로 이 API에서는 수정하지 않습니다.

---

## 사용자 삭제 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 사용자 삭제 API |
| 설명 | 사용자 ID를 이용하여 특정 사용자를 삭제하는 API |
| 엔드포인트(Endpoint) | `/api/v1/users/{user_id}/` |
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

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| user_id | integer | Y | 삭제할 사용자 ID |

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
| 없음 | - | 삭제 성공 시 응답 본문 없음 |

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

- 404 Not Found

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| detail | string | 존재하지 않는 사용자 ID로 요청한 경우의 에러 메시지 |

---

### 4. 비고

- 인증된 사용자만 삭제할 수 있습니다.
- 삭제된 사용자는 다시 조회할 수 없습니다.
- 실제 서비스에서는 물리 삭제 대신 비활성화 처리를 사용할 수 있습니다.