# 환자·진료기록 API 명세서

## 1. 공통 사항

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 데이터 형식 | JSON |
| 이미지 업로드 | `multipart/form-data` |
| 인증 방식 | `Authorization: Bearer {access_token}` |
| 날짜 형식 | ISO 8601 UTC |
| 최대 응답시간 | 3초 |
| 페이지 번호 | 0부터 시작 |
| 기본 페이지 크기 | 20개 |
| 최대 페이지 크기 | 100개 |

### 권한 기준

| 작업 | 허용 권한 |
| --- | --- |
| 환자 등록 | `MEDICAL` 부서의 `STAFF`, `ADMIN` |
| 진료기록 등록 | `MEDICAL` 부서의 `STAFF`, `ADMIN` |
| 환자·진료기록 조회 | `STAFF`, `ADMIN` |
| 환자 수정·삭제 | `STAFF`, `ADMIN` |
| 대기자 | 접근 불가 |

### 공통 성공 응답

```json
{
  "success": true,
  "data": {},
  "message": "요청이 정상적으로 처리되었습니다."
}
```

### 공통 오류 응답

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "fields": [
      {
        "field": "phoneNumber",
        "reason": "휴대폰 번호 형식이 올바르지 않습니다."
      }
    ]
  }
}
```

### 공통 상태 코드

| 상태 | 설명 |
| --- | --- |
| `200 OK` | 조회·수정 성공 |
| `201 Created` | 등록 성공 |
| `204 No Content` | 삭제 성공 |
| `400 Bad Request` | 입력값 또는 조회 조건 오류 |
| `401 Unauthorized` | 인증 실패 또는 Access Token 만료 |
| `403 Forbidden` | 접근 권한 부족 |
| `404 Not Found` | 환자 또는 진료기록 없음 |
| `409 Conflict` | 연락처·차트 번호 중복 등 데이터 충돌 |
| `413 Content Too Large` | 이미지 용량 초과 |
| `415 Unsupported Media Type` | 지원하지 않는 이미지 형식 |
| `500 Internal Server Error` | 서버 내부 오류 |

---

# 2. 환자 API

## 2.1 환자 정보 등록

- 요구사항: `REQ-PTNT-001`
- Method: `POST`
- URL: `/patients`
- 인증: 필요
- 권한: 의료 부서 `STAFF`, `ADMIN`

### 요청

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phoneNumber": "01012345678"
}
```

### 필드 검증

| 필드 | 타입 | 필수 | 검증 |
| --- | --- | --- | --- |
| `name` | string | 예 | 2~30자 |
| `age` | integer | 예 | 0~150 |
| `gender` | enum | 예 | `M`, `F` |
| `phoneNumber` | string | 예 | 하이픈 없는 숫자 10~11자리 |

### 성공 응답: `201 Created`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "name": "홍길동",
    "age": 45,
    "gender": "M",
    "phoneNumber": "01012345678",
    "createdAt": "2026-07-21T02:30:00Z",
    "updatedAt": null
  },
  "message": "환자 정보가 등록되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `VALIDATION_ERROR` | 필수값 누락 또는 형식 오류 |
| `403` | `MEDICAL_PERMISSION_REQUIRED` | 의료인 권한 없음 |
| `409` | `PHONE_NUMBER_ALREADY_EXISTS` | 동일 연락처가 이미 등록됨 |

---

## 2.2 환자 목록 조회

- 요구사항: `REQ-PTNT-002`
- Method: `GET`
- URL: `/patients`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### Query Parameters

| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `name` | string | 아니요 | - | 이름 부분 일치 검색 |
| `gender` | enum | 아니요 | - | `M`, `F` |
| `minAge` | integer | 아니요 | - | 최소 나이 |
| `maxAge` | integer | 아니요 | - | 최대 나이 |
| `page` | integer | 아니요 | `0` | 페이지 번호 |
| `size` | integer | 아니요 | `20` | 페이지 크기, 최대 100 |
| `sort` | string | 아니요 | `createdAt,desc` | 정렬 필드와 방향 |

### 요청 예시

```http
GET /api/v1/patients?name=홍&gender=M&minAge=30&maxAge=60&page=0&size=20
```

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 1001,
        "name": "홍길동",
        "age": 45,
        "gender": "M",
        "phoneNumber": "01012345678",
        "createdAt": "2026-07-21T02:30:00Z",
        "updatedAt": null
      }
    ],
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1,
    "first": true,
    "last": true
  },
  "message": "환자 목록을 조회했습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `INVALID_AGE_RANGE` | 최소 나이가 최대 나이보다 큼 |
| `400` | `INVALID_QUERY_PARAMETER` | 필터·정렬·페이지 조건 오류 |
| `403` | `STAFF_PERMISSION_REQUIRED` | 조회 권한 없음 |

---

## 2.3 환자 상세 조회

- 요구사항: `REQ-PTNT-003`
- Method: `GET`
- URL: `/patients/{patientId}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "name": "홍길동",
    "age": 45,
    "gender": "M",
    "phoneNumber": "01012345678"
  },
  "message": "환자 정보를 조회했습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `403` | `STAFF_PERMISSION_REQUIRED` | 조회 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | 환자가 존재하지 않음 |

---

## 2.4 환자 정보 수정

- 요구사항: `REQ-PTNT-004`
- Method: `PATCH`
- URL: `/patients/{patientId}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

`name`, `phoneNumber` 중 하나 이상을 전달한다. 전달하지 않은 항목은 기존 값을 유지한다.

### 요청

```json
{
  "name": "홍길순",
  "phoneNumber": "01098765432"
}
```

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 1001,
    "name": "홍길순",
    "age": 45,
    "gender": "M",
    "phoneNumber": "01098765432",
    "createdAt": "2026-07-21T02:30:00Z",
    "updatedAt": "2026-07-21T03:10:00Z"
  },
  "message": "환자 정보가 수정되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `EMPTY_UPDATE_REQUEST` | 수정할 필드가 없음 |
| `400` | `UNSUPPORTED_FIELD` | 나이·성별 등 수정 불가 필드 전달 |
| `404` | `PATIENT_NOT_FOUND` | 환자가 존재하지 않음 |
| `409` | `PHONE_NUMBER_ALREADY_EXISTS` | 변경할 연락처가 다른 환자와 중복 |

---

## 2.5 환자 정보 삭제

- 요구사항: `REQ-PTNT-005`
- Method: `DELETE`
- URL: `/patients/{patientId}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### 요청

삭제 확인 여부를 전달한다.

```json
{
  "confirmed": true
}
```

### 성공 응답: `204 No Content`

응답 본문은 반환하지 않는다.

### 삭제 범위

환자 삭제는 하나의 데이터베이스 트랜잭션으로 처리한다.

1. 환자의 X-Ray 이미지 파일 삭제
2. X-Ray 이미지 DB 정보 삭제
3. 관련 AI 분석 결과 삭제
4. 관련 진료기록 삭제
5. 환자 정보 삭제

파일 또는 DB 삭제 과정에서 오류가 발생하면 전체 삭제를 실패 처리한다.

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `DELETE_CONFIRMATION_REQUIRED` | 삭제 확인값이 `true`가 아님 |
| `404` | `PATIENT_NOT_FOUND` | 환자가 존재하지 않음 |
| `409` | `PATIENT_DELETE_FAILED` | 관련 데이터 또는 파일 삭제 실패 |

---

# 3. 진료기록 API

## 3.1 진료기록 등록

- 요구사항: `REQ-MDR-001`
- Method: `POST`
- URL: `/patients/{patientId}/medical-records`
- Content-Type: `multipart/form-data`
- 인증: 필요
- 권한: 의료 부서 `STAFF`, `ADMIN`

### Form Data

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `chartNumber` | string | 예 | 진료 차트 번호, 최대 50자 |
| `symptoms` | string | 예 | 증상 및 진료 내용 |
| `xrayImage` | binary | 예 | 흉부 X-Ray 이미지 |
| `shootingDatetime` | datetime | 아니요 | 촬영일시, 미입력 시 등록 시각 |

환자 ID는 URL의 `patientId`를 사용하므로 Form Data에 중복 전달하지 않는다.

### 요청 예시

```http
POST /api/v1/patients/1001/medical-records
Content-Type: multipart/form-data
Authorization: Bearer {access_token}
```

```text
chartNumber=CHART-2026-0001
symptoms=기침 및 흉통 증상이 지속됨
shootingDatetime=2026-07-21T02:00:00Z
xrayImage={binary}
```

### 이미지 정책

| 항목 | 정책 |
| --- | --- |
| 지원 형식 | JPEG, PNG, DICOM |
| 최대 용량 | 20MB |
| 저장 위치 | 서버 로컬 저장소 |
| 파일명 | UUID 기반 서버 생성 파일명 |
| 허용 확장자 | `.jpg`, `.jpeg`, `.png`, `.dcm` |
| 공개 경로 | 서버가 생성한 상대 URL 반환 |

클라이언트가 보낸 파일명을 저장 파일명으로 직접 사용하지 않는다.

### 성공 응답: `201 Created`

```json
{
  "success": true,
  "data": {
    "id": 5001,
    "patientId": 1001,
    "chartNumber": "CHART-2026-0001",
    "symptoms": "기침 및 흉통 증상이 지속됨",
    "xrayImage": {
      "id": 7001,
      "imageUrl": "/media/xrays/2026/07/550e8400-e29b-41d4-a716-446655440000.jpg",
      "shootingDatetime": "2026-07-21T02:00:00Z"
    },
    "createdAt": "2026-07-21T02:35:00Z"
  },
  "message": "진료기록이 등록되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `VALIDATION_ERROR` | 필수값 누락 또는 형식 오류 |
| `403` | `MEDICAL_PERMISSION_REQUIRED` | 의료인 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | 환자가 존재하지 않음 |
| `409` | `CHART_NUMBER_ALREADY_EXISTS` | 차트 번호 중복 |
| `413` | `XRAY_IMAGE_TOO_LARGE` | 이미지 용량 초과 |
| `415` | `UNSUPPORTED_XRAY_FORMAT` | 지원하지 않는 이미지 형식 |
| `500` | `XRAY_IMAGE_SAVE_FAILED` | 로컬 파일 저장 실패 |

DB 저장에 실패한 경우 먼저 저장된 이미지 파일을 제거한다.

---

## 3.2 진료기록 목록 조회

- 요구사항: `REQ-MDR-002`
- Method: `GET`
- URL: `/patients/{patientId}/medical-records`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### Query Parameters

| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `page` | integer | 아니요 | `0` | 페이지 번호 |
| `size` | integer | 아니요 | `20` | 페이지 크기, 최대 100 |
| `sort` | string | 아니요 | `createdAt,desc` | 정렬 조건 |

### 성공 응답: `200 OK`

`symptomsSummary`는 증상이 100자를 초과하면 처음 100자 뒤에 `…`를 붙인다.

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "id": 5001,
        "chartNumber": "CHART-2026-0001",
        "symptomsSummary": "기침 및 흉통 증상이 지속됨",
        "createdAt": "2026-07-21T02:35:00Z"
      }
    ],
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1,
    "first": true,
    "last": true
  },
  "message": "진료기록 목록을 조회했습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `INVALID_QUERY_PARAMETER` | 페이지 또는 정렬 조건 오류 |
| `404` | `PATIENT_NOT_FOUND` | 환자가 존재하지 않음 |

진료기록이 없는 경우 `404`가 아니라 빈 `content`와 `200`을 반환한다.

---

## 3.3 진료기록 상세 조회

- 요구사항: `REQ-MDR-003`
- Method: `GET`
- URL: `/patients/{patientId}/medical-records/{recordId}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### 성공 응답: `200 OK`

```json
{
  "success": true,
  "data": {
    "id": 5001,
    "patientId": 1001,
    "chartNumber": "CHART-2026-0001",
    "symptoms": "기침 및 흉통 증상이 지속됨",
    "xrayImage": {
      "id": 7001,
      "imageUrl": "/media/xrays/2026/07/550e8400-e29b-41d4-a716-446655440000.jpg",
      "shootingDatetime": "2026-07-21T02:00:00Z"
    },
    "createdAt": "2026-07-21T02:35:00Z"
  },
  "message": "진료기록을 조회했습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `404` | `PATIENT_NOT_FOUND` | 환자가 존재하지 않음 |
| `404` | `MEDICAL_RECORD_NOT_FOUND` | 진료기록이 존재하지 않음 |
| `404` | `MEDICAL_RECORD_PATIENT_MISMATCH` | 진료기록이 해당 환자의 기록이 아님 |

---

# 4. 오류 코드 목록

| 오류 코드 | HTTP | 설명 |
| --- | --- | --- |
| `VALIDATION_ERROR` | `400` | 입력값 검증 실패 |
| `INVALID_QUERY_PARAMETER` | `400` | 조회 조건 오류 |
| `INVALID_AGE_RANGE` | `400` | 나이 범위 오류 |
| `EMPTY_UPDATE_REQUEST` | `400` | 수정할 항목 없음 |
| `UNSUPPORTED_FIELD` | `400` | 수정 불가능한 필드 전달 |
| `DELETE_CONFIRMATION_REQUIRED` | `400` | 삭제 확인 필요 |
| `ACCESS_TOKEN_INVALID` | `401` | 유효하지 않은 Access Token |
| `ACCESS_TOKEN_EXPIRED` | `401` | Access Token 만료 |
| `STAFF_PERMISSION_REQUIRED` | `403` | 스태프 이상 권한 필요 |
| `MEDICAL_PERMISSION_REQUIRED` | `403` | 의료인 권한 필요 |
| `PATIENT_NOT_FOUND` | `404` | 환자를 찾을 수 없음 |
| `MEDICAL_RECORD_NOT_FOUND` | `404` | 진료기록을 찾을 수 없음 |
| `MEDICAL_RECORD_PATIENT_MISMATCH` | `404` | 환자와 진료기록 관계 불일치 |
| `PHONE_NUMBER_ALREADY_EXISTS` | `409` | 환자 연락처 중복 |
| `CHART_NUMBER_ALREADY_EXISTS` | `409` | 진료 차트 번호 중복 |
| `PATIENT_DELETE_FAILED` | `409` | 환자 관련 데이터 삭제 실패 |
| `XRAY_IMAGE_TOO_LARGE` | `413` | X-Ray 이미지 용량 초과 |
| `UNSUPPORTED_XRAY_FORMAT` | `415` | 지원하지 않는 이미지 형식 |
| `XRAY_IMAGE_SAVE_FAILED` | `500` | X-Ray 이미지 저장 실패 |

---

# 5. 요구사항 추적표

| 요구사항 ID | API |
| --- | --- |
| `REQ-PTNT-001` | `POST /patients` |
| `REQ-PTNT-002` | `GET /patients` |
| `REQ-PTNT-003` | `GET /patients/{patientId}` |
| `REQ-PTNT-004` | `PATCH /patients/{patientId}` |
| `REQ-PTNT-005` | `DELETE /patients/{patientId}` |
| `REQ-MDR-001` | `POST /patients/{patientId}/medical-records` |
| `REQ-MDR-002` | `GET /patients/{patientId}/medical-records` |
| `REQ-MDR-003` | `GET /patients/{patientId}/medical-records/{recordId}` |
| `NFR-PTNT-001` | 모든 환자 API |
| `NFR-MDR-001` | 모든 진료기록 API |

---

# 6. 확정이 필요한 정책

1. 환자·진료기록 등록 권한은 `department=MEDICAL`이면서 `role=STAFF` 이상인 사용자로 정의했다.
2. 환자 수정·삭제는 요구사항에 따라 의료 부서가 아닌 `STAFF`와 `ADMIN`에게도 허용했다.
3. 환자 연락처와 진료 차트 번호는 고유값으로 가정했다.
4. 환자 삭제 확인을 위해 `confirmed` 요청값을 추가했다.
5. 환자 삭제 시 AI 분석 결과도 관련 데이터에 포함해 삭제하도록 정의했다.
6. 이미지 최대 용량은 20MB, 지원 형식은 JPEG·PNG·DICOM으로 가정했다.
7. 하나의 진료기록에는 X-Ray 이미지 한 장이 등록되는 것으로 정의했다.
8. 진료기록 수정·삭제 기능은 요구사항에 없으므로 API에서 제외했다.
9. 실제 의료데이터에 법적 보존 의무가 있다면 영구 삭제 요구사항과 충돌할 수 있으므로 별도 정책 검토가 필요하다.
