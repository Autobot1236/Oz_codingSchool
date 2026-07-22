# 5일차 환자 관리 및 진료기록 API 설계

---

## 환자 정보 등록 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 등록 API |
| 요구사항 ID | REQ-PTNT-001 |
| 설명 | 의료진이 환자의 기본 정보를 등록하는 API |
| 엔드포인트(Endpoint) | `/api/v1/patients` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |
| Content-Type | application/json | 요청 타입 |

#### 본문 예시

```json
{
  "name": "김환자",
  "age": 45,
  "gender": "M",
  "phone": "01012345678"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| name | string | Y | 환자 이름. 1~30자 |
| age | integer | Y | 환자 나이. 0~150 사이의 정수 |
| gender | string | Y | 환자 성별. `M` 또는 `F` |
| phone | string | Y | 하이픈을 제외한 휴대폰 번호 10~11자리 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 201 Created

```json
{
  "id": 1,
  "name": "김환자",
  "age": 45,
  "gender": "M",
  "phone": "01012345678",
  "created_at": "2026-07-22T09:30:00Z",
  "updated_at": null
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 환자 고유 ID |
| name | string | 환자 이름 |
| age | integer | 환자 나이 |
| gender | string | 환자 성별 |
| phone | string | 환자 연락처 |
| created_at | datetime | 생성일시 |
| updated_at | datetime 또는 null | 수정일시. 수정 전에는 `null` |

#### 실패

- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 환자 등록 권한이 없는 경우
- 422 Unprocessable Entity: 필수 항목이 없거나 입력 형식이 잘못된 경우

```json
{
  "detail": "환자 정보를 올바르게 입력해주세요."
}
```

---

### 4. 비고

- 의료 부서의 `staff` 또는 `admin` 권한 사용자가 등록할 수 있습니다.
- 이름과 연락처의 앞뒤 공백을 제거한 후 저장합니다.
- 연락처는 숫자만 저장합니다.

---

## 환자 목록 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 목록 조회 API |
| 요구사항 ID | REQ-PTNT-002 |
| 설명 | 환자 목록을 조회하고 이름·성별·나이 범위로 검색 또는 필터링하는 API |
| 엔드포인트(Endpoint) | `/api/v1/patients` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | GET 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| name | string | N | 없음 | 이름 부분 일치 검색어 |
| gender | string | N | 없음 | 성별 필터. `M` 또는 `F` |
| min_age | integer | N | 없음 | 최소 나이. 해당 나이를 포함 |
| max_age | integer | N | 없음 | 최대 나이. 해당 나이를 포함 |
| page | integer | N | 1 | 조회할 페이지 번호 |
| size | integer | N | 20 | 한 페이지의 항목 수. 최대 100 |

#### 요청 예시

```http
GET /api/v1/patients?name=김&gender=M&min_age=40&max_age=60&page=1&size=20
Authorization: Bearer <access_token>
```

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "patients": [
    {
      "id": 1,
      "name": "김환자",
      "age": 45,
      "gender": "M",
      "phone": "01012345678",
      "created_at": "2026-07-22T09:30:00Z",
      "updated_at": null
    }
  ],
  "page": 1,
  "size": 20,
  "total": 1
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| patients | array | 환자 목록 |
| patients[].id | integer | 환자 고유 ID |
| patients[].name | string | 환자 이름 |
| patients[].age | integer | 환자 나이 |
| patients[].gender | string | 환자 성별 |
| patients[].phone | string | 환자 연락처 |
| patients[].created_at | datetime | 생성일시 |
| patients[].updated_at | datetime 또는 null | 수정일시 |
| page | integer | 현재 페이지 번호 |
| size | integer | 한 페이지의 항목 수 |
| total | integer | 조건에 맞는 전체 환자 수 |

#### 실패

- 400 Bad Request: `min_age`가 `max_age`보다 큰 경우
- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 환자 목록 조회 권한이 없는 경우
- 422 Unprocessable Entity: 필터 또는 페이지 값의 형식이 잘못된 경우

```json
{
  "detail": "나이 범위를 올바르게 입력해주세요."
}
```

---

### 4. 비고

- 검색 조건과 필터 조건을 함께 사용하면 모든 조건을 만족하는 환자만 조회합니다.
- 검색 결과가 없으면 `200 OK`와 빈 `patients` 배열을 반환합니다.
- 기본 정렬은 생성일시 내림차순입니다.

---

## 환자 정보 상세 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 상세 조회 API |
| 요구사항 ID | REQ-PTNT-003 |
| 설명 | 환자 고유 ID로 환자의 상세 정보를 조회하는 API |
| 엔드포인트(Endpoint) | `/api/v1/patients/{patient_id}` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 조회할 환자의 고유 ID |

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | GET 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터

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
  "name": "김환자",
  "age": 45,
  "gender": "M",
  "phone": "01012345678"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 환자 고유 ID |
| name | string | 환자 이름 |
| age | integer | 환자 나이 |
| gender | string | 환자 성별 |
| phone | string | 환자 연락처 |

#### 실패

- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 환자 상세 조회 권한이 없는 경우
- 404 Not Found: 환자가 존재하지 않는 경우

```json
{
  "detail": "환자를 찾을 수 없습니다."
}
```

---

### 4. 비고

- 로그인한 개발진, 의료 실무진, 연구진 중 `staff` 또는 `admin` 권한 사용자가 조회할 수 있습니다.

---

## 환자 정보 수정 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 수정 API |
| 요구사항 ID | REQ-PTNT-004 |
| 설명 | 환자의 이름 또는 연락처를 부분 수정하는 API |
| 엔드포인트(Endpoint) | `/api/v1/patients/{patient_id}` |
| 메서드(Method) | `PATCH` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |
| Content-Type | application/json | 요청 타입 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 수정할 환자의 고유 ID |

#### 본문 예시

```json
{
  "name": "김새이름",
  "phone": "01098765432"
}
```

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| name | string | N | 변경할 환자 이름. 1~30자 |
| phone | string | N | 변경할 휴대폰 번호. 하이픈 제외 10~11자리 |

#### 쿼리 파라미터

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
  "name": "김새이름",
  "age": 45,
  "gender": "M",
  "phone": "01098765432",
  "created_at": "2026-07-22T09:30:00Z",
  "updated_at": "2026-07-22T10:20:00Z"
}
```

#### 실패

- 400 Bad Request: 수정할 항목을 하나도 보내지 않은 경우
- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 환자 정보 수정 권한이 없는 경우
- 404 Not Found: 환자가 존재하지 않는 경우
- 422 Unprocessable Entity: 입력 형식이 잘못되거나 수정할 수 없는 필드를 보낸 경우

```json
{
  "detail": "수정할 환자 정보를 올바르게 입력해주세요."
}
```

---

### 4. 비고

- `PATCH` 방식으로 요청에 포함된 필드만 수정합니다.
- 요구사항에 따라 `name`, `phone`만 수정할 수 있습니다.
- `age`, `gender` 등 수정할 수 없는 필드는 허용하지 않습니다.

---

## 환자 정보 삭제 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 삭제 API |
| 요구사항 ID | REQ-PTNT-005 |
| 설명 | 환자와 관련된 진료기록 및 X-Ray 이미지를 함께 영구 삭제하는 API |
| 엔드포인트(Endpoint) | `/api/v1/patients/{patient_id}` |
| 메서드(Method) | `DELETE` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 삭제할 환자의 고유 ID |

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | DELETE 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 204 No Content
- 응답 본문 없음

#### 실패

- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 환자 정보 삭제 권한이 없는 경우
- 404 Not Found: 환자가 존재하지 않는 경우
- 500 Internal Server Error: 관련 데이터 또는 이미지 파일 삭제에 실패한 경우

```json
{
  "detail": "환자 정보 삭제 중 오류가 발생했습니다."
}
```

---

### 4. 비고

- 삭제 확인 팝업은 프론트엔드에서 제공하며 확인 후 이 API를 호출합니다.
- 환자 삭제 시 관련 진료기록, X-Ray 이미지 정보, AI 분석 결과를 함께 삭제합니다.
- DB의 연관 데이터뿐 아니라 로컬 저장소의 실제 X-Ray 이미지 파일도 삭제합니다.
- 연관 데이터 삭제는 트랜잭션으로 처리하여 일부 데이터만 삭제되지 않도록 합니다.

---

## 진료기록 등록 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 등록 API |
| 요구사항 ID | REQ-MDR-001 |
| 설명 | 의료진이 환자의 진료 정보와 흉부 X-Ray 이미지를 등록하는 API |
| 엔드포인트(Endpoint) | `/api/v1/medical-records` |
| 메서드(Method) | `POST` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |
| Content-Type | multipart/form-data | 파일을 포함한 요청 타입 |

#### Form Data

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 진료 대상 환자의 고유 ID |
| chart_number | string | Y | 진료 차트 넘버. 최대 50자이며 중복 불가 |
| symptoms | string | Y | 진료된 증상 |
| xray_image | file | Y | 촬영된 흉부 X-Ray 이미지 파일 |

#### 요청 예시

```http
POST /api/v1/medical-records
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

patient_id=1
chart_number=C-20260722-001
symptoms=고열과 기침, 호흡 곤란 증상이 있습니다.
xray_image=@chest-xray.jpg
```

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 201 Created

```json
{
  "id": 101,
  "patient_id": 1,
  "chart_number": "C-20260722-001",
  "symptoms": "고열과 기침, 호흡 곤란 증상이 있습니다.",
  "xray_images": [
    {
      "id": 501,
      "image_url": "/media/xrays/550e8400-e29b-41d4-a716-446655440000.jpg"
    }
  ],
  "created_at": "2026-07-22T09:30:00Z"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 진료기록 고유 ID |
| patient_id | integer | 환자 고유 ID |
| chart_number | string | 진료 차트 넘버 |
| symptoms | string | 진료된 증상 |
| xray_images | array | 등록된 X-Ray 이미지 목록 |
| xray_images[].id | integer | X-Ray 이미지 고유 ID |
| xray_images[].image_url | string | X-Ray 이미지 조회 경로 |
| created_at | datetime | 진료기록 생성일시 |

#### 실패

- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 진료기록 등록 권한이 없는 경우
- 404 Not Found: 선택한 환자가 존재하지 않는 경우
- 409 Conflict: 진료 차트 넘버가 이미 존재하는 경우
- 422 Unprocessable Entity: 필수 항목이 없거나 입력 형식이 잘못된 경우
- 500 Internal Server Error: 진료기록 또는 이미지 저장에 실패한 경우

```json
{
  "detail": "이미 존재하는 진료 차트 넘버입니다."
}
```

---

### 4. 비고

- 의료 부서의 `staff` 또는 `admin` 권한 사용자가 등록할 수 있습니다.
- 환자 검색은 환자 목록 조회 API의 `name` 검색 조건을 사용합니다.
- X-Ray 미리보기는 업로드 전에 프론트엔드에서 제공합니다.
- X-Ray 이미지는 서버가 실행되는 환경의 로컬 저장소에 저장합니다.
- 파일명 충돌을 방지하기 위해 서버에서 고유한 파일명을 생성하고 DB에는 이미지 조회 경로를 저장합니다.
- X-Ray 촬영일시는 별도 입력 요구사항이 없으므로 서버가 등록 시각을 저장합니다.
- 진료기록과 이미지 정보 저장에 실패하면 전체 작업을 롤백하고 저장 중 생성된 파일을 정리합니다.

---

## 진료기록 목록 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 목록 조회 API |
| 요구사항 ID | REQ-MDR-002 |
| 설명 | 특정 환자의 진료기록 목록을 조회하는 API |
| 엔드포인트(Endpoint) | `/api/v1/patients/{patient_id}/medical-records` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 진료기록을 조회할 환자의 고유 ID |

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | GET 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | integer | N | 1 | 조회할 페이지 번호 |
| size | integer | N | 20 | 한 페이지의 항목 수. 최대 100 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "medical_records": [
    {
      "id": 101,
      "chart_number": "C-20260722-001",
      "symptoms": "고열과 기침, 호흡 곤란 증상이 있습니다.",
      "created_at": "2026-07-22T09:30:00Z"
    }
  ],
  "page": 1,
  "size": 20,
  "total": 1
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| medical_records | array | 진료기록 목록 |
| medical_records[].id | integer | 진료기록 고유 ID |
| medical_records[].chart_number | string | 진료 차트 넘버 |
| medical_records[].symptoms | string | 증상. 100자 초과 시 뒤에 `…`를 붙여 생략 |
| medical_records[].created_at | datetime | 진료기록 생성일시 |
| page | integer | 현재 페이지 번호 |
| size | integer | 한 페이지의 항목 수 |
| total | integer | 해당 환자의 전체 진료기록 수 |

#### 실패

- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 진료기록 목록 조회 권한이 없는 경우
- 404 Not Found: 환자가 존재하지 않는 경우

```json
{
  "detail": "환자를 찾을 수 없습니다."
}
```

---

### 4. 비고

- 증상이 100자를 초과하면 앞의 100자 뒤에 `…`를 붙여 반환합니다.
- 진료기록이 없으면 `200 OK`와 빈 `medical_records` 배열을 반환합니다.
- 기본 정렬은 생성일시 내림차순입니다.

---

## 진료기록 상세 조회 API

### 1. API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 상세 조회 API |
| 요구사항 ID | REQ-MDR-003 |
| 설명 | 진료기록 고유 ID로 증상과 X-Ray 이미지를 상세 조회하는 API |
| 엔드포인트(Endpoint) | `/api/v1/medical-records/{record_id}` |
| 메서드(Method) | `GET` |
| 인증 필요 여부 | Y |

---

### 2. 요청(Request)

#### Headers

| Key | Value | 설명 |
| --- | --- | --- |
| Authorization | Bearer `<access_token>` | 인증 토큰 |

#### Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| record_id | integer | Y | 조회할 진료기록의 고유 ID |

#### 본문 필드

| 파라미터명 | 타입 | 필수 ( Y / N ) | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | GET 요청이므로 본문을 사용하지 않음 |

#### 쿼리 파라미터

| 쿼리 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| 없음 | - | - | 사용하지 않음 |

---

### 3. 응답(Response)

#### 성공

- 200 OK

```json
{
  "id": 101,
  "patient_id": 1,
  "chart_number": "C-20260722-001",
  "symptoms": "고열과 기침, 호흡 곤란 증상이 있습니다.",
  "xray_images": [
    {
      "id": 501,
      "image_url": "/media/xrays/550e8400-e29b-41d4-a716-446655440000.jpg"
    }
  ],
  "created_at": "2026-07-22T09:30:00Z"
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 진료기록 고유 ID |
| patient_id | integer | 환자 고유 ID |
| chart_number | string | 진료 차트 넘버 |
| symptoms | string | 생략하지 않은 전체 증상 |
| xray_images | array | X-Ray 이미지 목록 |
| xray_images[].id | integer | X-Ray 이미지 고유 ID |
| xray_images[].image_url | string | X-Ray 이미지 조회 경로 |
| created_at | datetime | 진료기록 생성일시 |

#### 실패

- 401 Unauthorized: 인증 정보가 유효하지 않은 경우
- 403 Forbidden: 진료기록 상세 조회 권한이 없는 경우
- 404 Not Found: 진료기록이 존재하지 않는 경우

```json
{
  "detail": "진료기록을 찾을 수 없습니다."
}
```

---

### 4. 비고

- 목록 조회와 달리 증상 전체 내용을 반환합니다.
- `image_url`에는 서버 내부의 절대 파일 경로가 아닌 `/media/...` 형식의 조회 경로를 반환합니다.
- 로그인한 개발진, 의료 실무진, 연구진 중 `staff` 또는 `admin` 권한 사용자가 조회할 수 있습니다.

---

## 공통 비기능 요구사항

| 항목 | 내용 |
| --- | --- |
| 인증 및 인가 | 모든 API는 JWT 인증을 사용하며, 역할과 부서에 따라 접근 권한을 확인합니다. |
| 대기자 권한 | `pending` 사용자는 환자 및 진료기록 API에 접근할 수 없습니다. |
| 날짜 형식 | 날짜·시간은 ISO 8601 형식으로 반환합니다. 예: `2026-07-22T09:30:00Z` |
| 오류 형식 | 오류 응답은 `{"detail": "오류 메시지"}` 형식을 사용합니다. |
| 로컬 이미지 저장 | X-Ray 이미지는 서버 실행 환경의 로컬 저장소에 저장하고 DB에는 조회 경로를 저장합니다. |
| 삭제 정책 | 환자 삭제 시 관련 진료기록과 X-Ray 이미지 데이터 및 실제 이미지 파일을 함께 삭제합니다. |
| API 성능 | `NFR-PTNT-001`, `NFR-MDR-001`에 따라 모든 환자 및 진료기록 API는 최대 3초 이내에 처리하고 응답합니다. |

진료기록 자체의 수정 및 개별 삭제는 제공된 요구사항에 포함되어 있지 않으므로 이번 API 설계 범위에서 제외합니다.
