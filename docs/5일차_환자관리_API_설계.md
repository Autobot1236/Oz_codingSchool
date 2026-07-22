# 환자·진료기록 API 명세서

## 1. 공통 규칙

### 1.1 기본 정보

| 항목 | 내용 |
| --- | --- |
| Base URL | `/api/v1` |
| 데이터 형식 | `application/json` |
| 이미지 업로드 | `multipart/form-data` |
| 인증 방식 | JWT Bearer Token |
| 날짜 형식 | ISO 8601 UTC |
| 최대 응답시간 | 3초 |
| JSON 필드 | `snake_case` |
| 페이지 번호 | 0부터 시작 |
| 기본 페이지 크기 | 20 |
| 최대 페이지 크기 | 100 |

### 1.2 인증 헤더

```http
Authorization: Bearer {access_token}
```

### 1.3 권한 기준

| 작업 | 허용 조건 |
| --- | --- |
| 환자 등록 | `role=ADMIN` 또는 `role=STAFF AND department=MEDICAL` |
| 진료기록 등록 | `role=ADMIN` 또는 `role=STAFF AND department=MEDICAL` |
| 환자 조회 | `STAFF`, `ADMIN` |
| 환자 수정·삭제 | `STAFF`, `ADMIN` |
| 진료기록 조회 | `STAFF`, `ADMIN` |
| 대기자 | 접근 불가 |

관리자 권한은 URL이 아닌 서버의 `require_admin` Dependency를 통해 검사한다.

### 1.4 Enum

| 구분 | API 값 |
| --- | --- |
| Gender | `M`, `F` |
| Department | `MEDICAL`, `DEV`, `RESEARCH` |
| Role | `PENDING`, `STAFF`, `ADMIN` |

화면의 한글 표기는 프론트엔드에서 별도로 매핑한다.

### 1.5 공통 오류 응답

```json
{
  "detail": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해 주세요.",
    "fields": [
      {
        "field": "phone_number",
        "reason": "휴대폰 번호 형식이 올바르지 않습니다."
      }
    ]
  }
}
```

`fields`는 필드 단위 오류가 있을 때만 반환한다.

### 1.6 HTTP 상태 코드

| 상태 코드 | 설명 |
| --- | --- |
| `200 OK` | 조회·수정 성공 |
| `201 Created` | 등록 성공 |
| `204 No Content` | 삭제 성공 |
| `400 Bad Request` | 빈 수정 요청 또는 잘못된 조회 조건 |
| `401 Unauthorized` | 미인증 또는 Access Token 만료·변조 |
| `403 Forbidden` | 권한 부족 |
| `404 Not Found` | 대상 리소스 없음 |
| `409 Conflict` | 연락처·차트 번호 중복 |
| `413 Content Too Large` | 이미지 용량 초과 |
| `415 Unsupported Media Type` | 지원하지 않는 이미지 형식 |
| `422 Unprocessable Entity` | 요청 필드 형식 검증 실패 |
| `500 Internal Server Error` | 서버 내부 오류 |

---

# 2. 환자 API

## 2.1 환자 정보 등록

- 요구사항: `REQ-PTNT-001`
- Method: `POST`
- URL: `/api/v1/patients`
- 인증: 필요
- 권한: `ADMIN` 또는 의료 부서 `STAFF`

### 요청

```json
{
  "name": "홍길동",
  "age": 45,
  "gender": "M",
  "phone_number": "01012345678"
}
```

### 요청 필드

| 필드 | 타입 | 필수 | 검증 |
| --- | --- | --- | --- |
| `name` | string | 예 | 공백 제거 후 2~30자 |
| `age` | integer | 예 | 0~150 |
| `gender` | enum | 예 | `M`, `F` |
| `phone_number` | string | 예 | 하이픈 없는 숫자 10~11자리 |

### 성공 응답: `201 Created`

```json
{
  "patient": {
    "id": 1001,
    "name": "홍길동",
    "age": 45,
    "gender": "M",
    "phone_number": "01012345678",
    "created_at": "2026-07-22T02:30:00Z",
    "updated_at": null
  },
  "message": "환자 정보가 등록되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `401` | `ACCESS_TOKEN_REQUIRED` | 인증정보 없음 |
| `403` | `MEDICAL_PERMISSION_REQUIRED` | 환자 등록 권한 없음 |
| `409` | `PHONE_NUMBER_ALREADY_EXISTS` | 연락처 중복 |
| `422` | `VALIDATION_ERROR` | 필수값 누락 또는 형식 오류 |

---

## 2.2 환자 목록 조회

- 요구사항: `REQ-PTNT-002`
- Method: `GET`
- URL: `/api/v1/patients`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### Query Parameters

| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `name` | string | 아니요 | - | 이름 부분 일치 검색 |
| `gender` | enum | 아니요 | - | `M`, `F` |
| `min_age` | integer | 아니요 | - | 최소 나이 |
| `max_age` | integer | 아니요 | - | 최대 나이 |
| `page` | integer | 아니요 | `0` | 페이지 번호 |
| `size` | integer | 아니요 | `20` | 페이지 크기, 최대 100 |
| `sort` | string | 아니요 | `created_at,desc` | 정렬 필드와 방향 |

### 요청 예시

```http
GET /api/v1/patients?name=홍&gender=M&min_age=30&max_age=60&page=0&size=20&sort=created_at,desc
```

### 성공 응답: `200 OK`

```json
{
  "patients": [
    {
      "id": 1001,
      "name": "홍길동",
      "age": 45,
      "gender": "M",
      "phone_number": "01012345678",
      "created_at": "2026-07-22T02:30:00Z",
      "updated_at": null
    }
  ],
  "page": 0,
  "size": 20,
  "total_elements": 1,
  "total_pages": 1,
  "first": true,
  "last": true
}
```

조회 결과가 없으면 `404`가 아니라 빈 목록을 반환한다.

```json
{
  "patients": [],
  "page": 0,
  "size": 20,
  "total_elements": 0,
  "total_pages": 0,
  "first": true,
  "last": true
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `INVALID_AGE_RANGE` | `min_age`가 `max_age`보다 큼 |
| `400` | `INVALID_QUERY_PARAMETER` | 페이지 또는 정렬 조건 오류 |
| `403` | `STAFF_PERMISSION_REQUIRED` | 조회 권한 없음 |
| `422` | `VALIDATION_ERROR` | 성별·나이 필드 형식 오류 |

---

## 2.3 환자 상세 조회

- 요구사항: `REQ-PTNT-003`
- Method: `GET`
- URL: `/api/v1/patients/{patient_id}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### Path Parameter

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `patient_id` | integer | 조회할 Patient 고유 ID |

### 성공 응답: `200 OK`

```json
{
  "patient": {
    "id": 1001,
    "name": "홍길동",
    "age": 45,
    "gender": "M",
    "phone_number": "01012345678"
  }
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `403` | `STAFF_PERMISSION_REQUIRED` | 조회 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | Patient가 존재하지 않음 |
| `422` | `VALIDATION_ERROR` | `patient_id` 형식 오류 |

---

## 2.4 환자 정보 수정

- 요구사항: `REQ-PTNT-004`
- Method: `PATCH`
- URL: `/api/v1/patients/{patient_id}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

`name`, `phone_number` 중 하나 이상을 전달한다. 전달하지 않은 필드는 기존 값을 유지한다.

### 요청 예시

```json
{
  "name": "홍길순",
  "phone_number": "01098765432"
}
```

### 수정 가능 필드

| 필드 | 타입 | 검증 |
| --- | --- | --- |
| `name` | string | 공백 제거 후 2~30자 |
| `phone_number` | string | 하이픈 없는 숫자 10~11자리 |

### 성공 응답: `200 OK`

```json
{
  "patient": {
    "id": 1001,
    "name": "홍길순",
    "age": 45,
    "gender": "M",
    "phone_number": "01098765432",
    "created_at": "2026-07-22T02:30:00Z",
    "updated_at": "2026-07-22T03:10:00Z"
  },
  "message": "환자 정보가 수정되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `EMPTY_UPDATE_REQUEST` | 수정할 필드가 없음 |
| `400` | `UNSUPPORTED_FIELD` | 나이·성별 등 수정 불가능한 필드 전달 |
| `404` | `PATIENT_NOT_FOUND` | Patient가 존재하지 않음 |
| `409` | `PHONE_NUMBER_ALREADY_EXISTS` | 다른 Patient의 연락처와 중복 |
| `422` | `VALIDATION_ERROR` | 이름 또는 연락처 형식 오류 |

---

## 2.5 환자 정보 삭제

- 요구사항: `REQ-PTNT-005`
- Method: `DELETE`
- URL: `/api/v1/patients/{patient_id}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

삭제 확인 모달은 프론트엔드에서 처리한다. 사용자가 확인한 경우에만 DELETE API를 호출한다.

DELETE 요청 본문은 사용하지 않는다.

### 성공 응답: `204 No Content`

응답 본문을 반환하지 않는다.

### DB 삭제 범위

Patient 삭제 시 다음 DB 데이터에 `ON DELETE CASCADE` 정책을 적용한다.

```text
Patient
 └─ MedicalRecord
     ├─ XrayImage
     └─ AIAnalysisResult
```

### 로컬 파일 삭제 처리

1. 삭제할 X-Ray 파일 경로를 조회한다.
2. DB 트랜잭션에서 관련 데이터를 삭제한다.
3. DB 트랜잭션을 commit한다.
4. 로컬 X-Ray 파일을 삭제한다.
5. 파일 삭제 실패 시 오류 로그와 재처리 대상을 기록한다.

로컬 파일시스템 작업은 DB 트랜잭션으로 rollback할 수 없으므로 DB 삭제와 별도로 처리한다.

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `403` | `STAFF_PERMISSION_REQUIRED` | 삭제 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | Patient가 존재하지 않음 |
| `409` | `PATIENT_DELETE_CONFLICT` | 연관 데이터 삭제 충돌 |
| `500` | `XRAY_FILE_DELETE_FAILED` | X-Ray 파일 삭제 및 재처리 등록 실패 |

---

# 3. 진료기록 API

## 3.1 진료기록 등록

- 요구사항: `REQ-MDR-001`
- Method: `POST`
- URL: `/api/v1/patients/{patient_id}/medical-records`
- Content-Type: `multipart/form-data`
- 인증: 필요
- 권한: `ADMIN` 또는 의료 부서 `STAFF`

### Path Parameter

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `patient_id` | integer | MedicalRecord를 등록할 Patient ID |

### Form Data

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `chart_number` | string | 예 | 진료 차트 번호, 최대 50자 |
| `symptoms` | string | 예 | 증상 및 진료 내용 |
| `xray_image` | binary | 예 | 흉부 X-Ray 이미지 |
| `shooting_datetime` | datetime | 아니요 | 촬영일시, 미입력 시 등록 시각 |

Patient ID는 URL의 `patient_id`를 사용하므로 Form Data에 중복 전달하지 않는다.

### 요청 예시

```http
POST /api/v1/patients/1001/medical-records
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

```text
chart_number=CHART-2026-0001
symptoms=기침 및 흉통 증상이 지속됨
shooting_datetime=2026-07-22T02:00:00Z
xray_image={binary}
```

### 이미지 정책

| 항목 | 정책 |
| --- | --- |
| 지원 형식 | JPEG, PNG, DICOM |
| 최대 용량 | 20MB |
| 저장 위치 | 서버 로컬 저장소 |
| 저장 파일명 | UUID 기반 서버 생성 파일명 |
| 허용 확장자 | `.jpg`, `.jpeg`, `.png`, `.dcm` |
| 반환 경로 | 서버가 생성한 상대 URL |

클라이언트가 전송한 원본 파일명을 서버 저장 파일명으로 직접 사용하지 않는다.

### 성공 응답: `201 Created`

```json
{
  "medical_record": {
    "id": 5001,
    "patient_id": 1001,
    "chart_number": "CHART-2026-0001",
    "symptoms": "기침 및 흉통 증상이 지속됨",
    "xray_image": {
      "id": 7001,
      "image_url": "/media/xrays/2026/07/550e8400-e29b-41d4-a716-446655440000.jpg",
      "shooting_datetime": "2026-07-22T02:00:00Z"
    },
    "created_at": "2026-07-22T02:35:00Z"
  },
  "message": "진료기록이 등록되었습니다."
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `403` | `MEDICAL_PERMISSION_REQUIRED` | 진료기록 등록 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | Patient가 존재하지 않음 |
| `409` | `CHART_NUMBER_ALREADY_EXISTS` | 차트 번호 중복 |
| `413` | `XRAY_IMAGE_TOO_LARGE` | 이미지 용량 초과 |
| `415` | `UNSUPPORTED_XRAY_FORMAT` | 지원하지 않는 이미지 형식 |
| `422` | `VALIDATION_ERROR` | 필수값 누락 또는 필드 형식 오류 |
| `500` | `XRAY_IMAGE_SAVE_FAILED` | 로컬 파일 저장 실패 |

DB 저장에 실패하면 해당 요청에서 먼저 저장된 X-Ray 파일을 제거한다.

---

## 3.2 진료기록 목록 조회

- 요구사항: `REQ-MDR-002`
- Method: `GET`
- URL: `/api/v1/patients/{patient_id}/medical-records`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### Query Parameters

| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `page` | integer | 아니요 | `0` | 페이지 번호 |
| `size` | integer | 아니요 | `20` | 페이지 크기, 최대 100 |
| `sort` | string | 아니요 | `created_at,desc` | 정렬 조건 |

### 성공 응답: `200 OK`

`symptoms_summary`는 증상이 100자를 초과하면 처음 100자 뒤에 `…`를 붙인다.

```json
{
  "medical_records": [
    {
      "id": 5001,
      "chart_number": "CHART-2026-0001",
      "symptoms_summary": "기침 및 흉통 증상이 지속됨",
      "created_at": "2026-07-22T02:35:00Z"
    }
  ],
  "page": 0,
  "size": 20,
  "total_elements": 1,
  "total_pages": 1,
  "first": true,
  "last": true
}
```

MedicalRecord가 없으면 `404`가 아니라 빈 목록과 `200`을 반환한다.

```json
{
  "medical_records": [],
  "page": 0,
  "size": 20,
  "total_elements": 0,
  "total_pages": 0,
  "first": true,
  "last": true
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `400` | `INVALID_QUERY_PARAMETER` | 페이지 또는 정렬 조건 오류 |
| `403` | `STAFF_PERMISSION_REQUIRED` | 조회 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | Patient가 존재하지 않음 |
| `422` | `VALIDATION_ERROR` | `patient_id` 형식 오류 |

---

## 3.3 진료기록 상세 조회

- 요구사항: `REQ-MDR-003`
- Method: `GET`
- URL: `/api/v1/patients/{patient_id}/medical-records/{record_id}`
- 인증: 필요
- 권한: `STAFF`, `ADMIN`

### Path Parameters

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `patient_id` | integer | Patient 고유 ID |
| `record_id` | integer | MedicalRecord 고유 ID |

### 성공 응답: `200 OK`

```json
{
  "medical_record": {
    "id": 5001,
    "patient_id": 1001,
    "chart_number": "CHART-2026-0001",
    "symptoms": "기침 및 흉통 증상이 지속됨",
    "xray_image": {
      "id": 7001,
      "image_url": "/media/xrays/2026/07/550e8400-e29b-41d4-a716-446655440000.jpg",
      "shooting_datetime": "2026-07-22T02:00:00Z"
    },
    "created_at": "2026-07-22T02:35:00Z"
  }
}
```

### 오류

| 상태 | 오류 코드 | 조건 |
| --- | --- | --- |
| `403` | `STAFF_PERMISSION_REQUIRED` | 조회 권한 없음 |
| `404` | `PATIENT_NOT_FOUND` | Patient가 존재하지 않음 |
| `404` | `MEDICAL_RECORD_NOT_FOUND` | MedicalRecord가 존재하지 않음 |
| `404` | `MEDICAL_RECORD_PATIENT_MISMATCH` | MedicalRecord가 해당 Patient의 기록이 아님 |
| `422` | `VALIDATION_ERROR` | Path Parameter 형식 오류 |

---

# 4. 오류 코드 목록

| 오류 코드 | HTTP | 설명 |
| --- | --- | --- |
| `VALIDATION_ERROR` | `422` | 요청 필드 형식 검증 실패 |
| `INVALID_QUERY_PARAMETER` | `400` | 조회 조건 오류 |
| `INVALID_AGE_RANGE` | `400` | 나이 범위 오류 |
| `EMPTY_UPDATE_REQUEST` | `400` | 수정할 항목 없음 |
| `UNSUPPORTED_FIELD` | `400` | 수정 불가능한 필드 전달 |
| `ACCESS_TOKEN_REQUIRED` | `401` | Access Token 없음 |
| `ACCESS_TOKEN_INVALID` | `401` | Access Token 변조 또는 형식 오류 |
| `ACCESS_TOKEN_EXPIRED` | `401` | Access Token 만료 |
| `STAFF_PERMISSION_REQUIRED` | `403` | Staff 이상 권한 필요 |
| `MEDICAL_PERMISSION_REQUIRED` | `403` | 의료인 또는 Admin 권한 필요 |
| `PATIENT_NOT_FOUND` | `404` | Patient를 찾을 수 없음 |
| `MEDICAL_RECORD_NOT_FOUND` | `404` | MedicalRecord를 찾을 수 없음 |
| `MEDICAL_RECORD_PATIENT_MISMATCH` | `404` | Patient와 MedicalRecord 관계 불일치 |
| `PHONE_NUMBER_ALREADY_EXISTS` | `409` | Patient 연락처 중복 |
| `CHART_NUMBER_ALREADY_EXISTS` | `409` | 진료 차트 번호 중복 |
| `PATIENT_DELETE_CONFLICT` | `409` | Patient 관련 DB 데이터 삭제 충돌 |
| `XRAY_IMAGE_TOO_LARGE` | `413` | X-Ray 이미지 용량 초과 |
| `UNSUPPORTED_XRAY_FORMAT` | `415` | 지원하지 않는 X-Ray 형식 |
| `XRAY_IMAGE_SAVE_FAILED` | `500` | X-Ray 이미지 저장 실패 |
| `XRAY_FILE_DELETE_FAILED` | `500` | X-Ray 파일 삭제 및 재처리 등록 실패 |

---

# 5. 코드 구조

구현 시 다음 책임 분리 규칙을 적용한다.

| 경로 | 책임 |
| --- | --- |
| `app/apis/patients.py` | Patient HTTP 요청·응답·Dependency |
| `app/apis/medical_records.py` | MedicalRecord HTTP 요청·응답·Dependency |
| `app/schemas/patients.py` | Patient Pydantic 요청·응답 모델 |
| `app/schemas/medical_records.py` | MedicalRecord Pydantic 모델 |
| `app/services/patients.py` | Patient 업무 규칙과 트랜잭션 |
| `app/services/medical_records.py` | MedicalRecord 및 파일 저장 업무 규칙 |
| `app/repositories/patients.py` | Patient DB 조회·저장 |
| `app/repositories/medical_records.py` | MedicalRecord DB 조회·저장 |
| `app/models/patient.py` | `Patient` 및 `patients` 테이블 |
| `app/models/medical_record.py` | `MedicalRecord` 및 `medical_records` 테이블 |
| `app/models/xray_image.py` | `XrayImage` 및 `xray_images` 테이블 |
| `app/models/ai_analysis_result.py` | `AIAnalysisResult` 및 `ai_analysis_results` 테이블 |

DB 작업은 `AsyncSession`, `select()`, `await` 방식으로 통일하고 `commit()`과 `rollback()`은 Service 계층에서만 수행한다.

---

# 6. 요구사항 추적표

| 요구사항 ID | API |
| --- | --- |
| `REQ-PTNT-001` | `POST /api/v1/patients` |
| `REQ-PTNT-002` | `GET /api/v1/patients` |
| `REQ-PTNT-003` | `GET /api/v1/patients/{patient_id}` |
| `REQ-PTNT-004` | `PATCH /api/v1/patients/{patient_id}` |
| `REQ-PTNT-005` | `DELETE /api/v1/patients/{patient_id}` |
| `REQ-MDR-001` | `POST /api/v1/patients/{patient_id}/medical-records` |
| `REQ-MDR-002` | `GET /api/v1/patients/{patient_id}/medical-records` |
| `REQ-MDR-003` | `GET /api/v1/patients/{patient_id}/medical-records/{record_id}` |
| `NFR-PTNT-001` | 모든 Patient API |
| `NFR-MDR-001` | 모든 MedicalRecord API |

---

# 7. 확정 정책

1. Admin은 부서와 관계없이 Patient와 MedicalRecord를 등록할 수 있다.
2. Staff는 `department=MEDICAL`일 때만 Patient와 MedicalRecord를 등록할 수 있다.
3. Patient 연락처와 MedicalRecord 차트 번호는 고유값으로 관리한다.
4. Patient 삭제 확인은 프론트엔드 모달에서 처리하며 DELETE 본문을 사용하지 않는다.
5. Patient 삭제 시 관련 MedicalRecord, XrayImage, AIAnalysisResult DB 데이터도 삭제한다.
6. X-Ray 파일은 DB 삭제 완료 후 제거하며 실패 시 재처리 대상으로 기록한다.
7. X-Ray 최대 용량은 20MB로 제한한다.
8. 지원 파일 형식은 JPEG, PNG, DICOM으로 제한한다.
9. 하나의 MedicalRecord에는 XrayImage 한 장을 등록한다.
10. MedicalRecord 수정·삭제 기능은 현재 요구사항 범위에서 제외한다.
11. 실제 환자 정보, 연락처, 진료기록 및 X-Ray 이미지는 저장소나 테스트 Fixture에 포함하지 않는다.
12. 의료데이터 법적 보존 의무가 있는 경우 영구 삭제 요구사항과 별도로 검토한다.
