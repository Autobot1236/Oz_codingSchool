# 5일차 - 환자 관리 및 진료기록 API 설계

## 1. 개요

| 항목 | 내용 |
| --- | --- |
| 대상 도메인 | Patient(환자), MedicalRecord(진료기록), XrayImage(X-Ray 이미지) |
| 배경 | 폐렴 환자 관리 백오피스에서 환자 정보와 환자의 진료기록을 관리하기 위한 API 설계 |
| 범위 포함 | 환자 등록/목록 조회/상세 조회/수정/삭제, 진료기록 등록/목록 조회/상세 조회 |
| 범위 제외 | AI 판독 결과 생성, 로그인/회원가입, 프론트엔드 화면 구현 |
| 참고 문서 | `5일차 - 진료기록 사용자 요구사항 정의서`, [`3일차_db_migration.md`](./3일차_db_migration.md), [`4일차_USER_요구사항_정의서.md`](./4일차_USER_요구사항_정의서.md) |

---

## 2. 요구사항 요약

### 2-1. 환자 관리 요구사항

| ID | 기능명 | 설명 |
| --- | --- | --- |
| REQ-PTNT-001 | 환자 정보 등록 | 사내 의료인 역할의 사용자가 환자 정보를 등록한다. |
| REQ-PTNT-002 | 환자 목록 조회 | 로그인한 사내 사용자가 환자 목록을 검색/필터링하여 조회한다. |
| REQ-PTNT-003 | 환자 정보 상세 조회 | 환자 상세 페이지에서 환자 기본 정보를 조회한다. |
| REQ-PTNT-004 | 환자 정보 수정 | 환자 상세 페이지에서 환자 이름과 연락처를 수정한다. |
| REQ-PTNT-005 | 환자 정보 삭제 | 환자와 관련 진료기록, X-Ray 이미지를 함께 삭제한다. |

### 2-2. 진료기록 요구사항

| ID | 기능명 | 설명 |
| --- | --- | --- |
| REQ-MDR-001 | 진료기록 등록 | 사내 의료인 역할의 사용자가 환자 진료정보와 X-Ray 이미지를 등록한다. |
| REQ-MDR-002 | 진료기록 목록 조회 | 환자 상세 페이지에서 해당 환자의 진료기록 목록을 조회한다. |
| REQ-MDR-003 | 진료기록 상세 조회 | 선택한 진료기록의 상세 정보와 X-Ray 이미지를 조회한다. |

---

## 3. 공통 API 규칙

### 3-1. 기본 경로

| 구분 | 기본 경로 |
| --- | --- |
| 환자 관리 API | `/api/v1/patients` |
| 진료기록 API | `/api/v1/medical-records` |

### 3-2. 인증 방식

환자 관리 및 진료기록 API는 내부 백오피스 기능이므로 기본적으로 로그인한 사용자만 호출할 수 있다.

요청 시 access token을 `Authorization` 헤더에 포함한다.

```http
Authorization: Bearer {access_token}
```

인증 토큰이 없거나 유효하지 않으면 `401 Unauthorized`를 반환한다.

### 3-3. 권한 기준

`app/models/enums.py`의 `Role`, `Department` 기준으로 접근 권한을 구분한다.

| 구분 | 허용 대상 | 설명 |
| --- | --- | --- |
| 조회 기능 | `STAFF`, `ADMIN` | 환자 목록/상세 조회, 진료기록 목록/상세 조회 |
| 등록/수정/삭제 기능 | `STAFF`, `ADMIN` | 환자 등록/수정/삭제, 진료기록 등록 |
| 접근 불가 | `PENDING` | 권한 부여 대기 상태이므로 환자/진료기록 API 접근 불가 |

부서 기준으로는 요구사항 정의서에 명시된 사내 의료실무진, 개발진, 연구진을 `MEDICAL`, `DEV`, `RESEARCH`로 매핑한다. 실제 구현 시에는 `role=STAFF` 이상인지 먼저 확인하고, 필요한 경우 `department` 기준으로 세부 접근 범위를 추가한다.

환자/진료기록 도메인의 조회 API는 `STAFF`, `ADMIN` 권한을 허용한다. 등록/수정/삭제 API는 `STAFF`, `ADMIN` 권한을 기본으로 하되, 실제 의료 업무 등록 기능은 `department=MEDICAL` 조건을 추가로 검토한다.

권한이 부족하면 `403 Forbidden`을 반환한다.

### 3-4. 공통 응답 형식

성공 응답은 API별 데이터 구조를 명확히 반환한다.

```json
{
  "data": {},
  "message": "요청이 성공적으로 처리되었습니다."
}
```

목록 조회 응답은 페이지네이션 정보를 함께 반환한다.

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 100
  }
}
```

### 3-5. 날짜 형식

`created_at`, `updated_at`, `shooting_datetime`은 ISO 8601 문자열 형식으로 반환한다.

```text
2026-07-20T15:30:00
```

### 3-6. 페이지네이션 및 정렬

목록 조회 API는 기본적으로 아래 쿼리 파라미터를 사용한다.

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `page` | integer | N | 1 | 조회할 페이지 번호 |
| `size` | integer | N | 20 | 페이지당 조회 개수 |
| `sort` | string | N | `created_at:desc` | 정렬 기준 |

### 3-7. 이미지 업로드 형식

진료기록 등록 API는 X-Ray 이미지 파일을 함께 업로드해야 하므로 `application/json`이 아니라 `multipart/form-data`를 사용한다.

텍스트 필드는 `Form()`, 파일 필드는 `UploadFile`로 받는 구조를 사용한다.

| 필드 | 전달 방식 | 설명 |
| --- | --- | --- |
| `patient_id` | Form | 환자 고유 ID |
| `chart_number` | Form | 진료 차트 번호 |
| `symptoms` | Form | 진료된 증상 |
| `xray_image` | UploadFile | 촬영된 흉부 X-Ray 이미지 |

FastAPI에서 파일 업로드가 포함된 요청은 `multipart/form-data`로 파싱되므로, 일반적인 JSON `BaseModel` 요청 본문과 `File`을 그대로 섞어 쓰기 어렵다. 필요하다면 Pydantic 모델에 `as_form` 메서드를 정의하여 Form 데이터를 모델처럼 다루는 방식으로 우회할 수 있다.

---

## 4. 환자 관리 API

### 4-1. 환자 정보 등록

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PTNT-001 |
| Method | `POST` |
| URL | `/api/v1/patients` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| Content-Type | `application/json` |
| 설명 | 환자 관리 메뉴에서 환자 정보를 등록한다. |

#### 요청 Body

| 필드 | 타입 | 필수 | 설명 | 제약 조건 |
| --- | --- | --- | --- | --- |
| `name` | string | Y | 환자 이름 | 최대 30자 |
| `age` | integer | Y | 환자 나이 | 0 이상 |
| `gender` | string | Y | 환자 성별 | `M`, `F` 중 하나 |
| `phone` | string | Y | 환자 연락처 | 숫자 11자리 |

#### 요청 예시

```json
{
  "name": "김환자",
  "age": 45,
  "gender": "M",
  "phone": "01012345678"
}
```

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `201 Created` | 환자 정보 등록 성공 |

```json
{
  "data": {
    "id": 1,
    "name": "김환자",
    "age": 45,
    "gender": "M",
    "phone": "01012345678",
    "created_at": "2026-07-20T15:30:00",
    "updated_at": null
  },
  "message": "환자 정보가 등록되었습니다."
}
```

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 환자 등록 권한이 없는 경우 |
| `422 Unprocessable Entity` | 필수 입력값이 누락되었거나 형식이 올바르지 않은 경우 |

### 4-2. 환자 목록 조회

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PTNT-002 |
| Method | `GET` |
| URL | `/api/v1/patients` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| 설명 | 환자 목록을 조회하고, 이름 검색 및 성별/나이 범위 필터링을 제공한다. |

#### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
| --- | --- | --- | --- | --- |
| `name` | string | N | 환자 이름 검색어 | `김` |
| `gender` | string | N | 성별 필터 | `M` |
| `min_age` | integer | N | 최소 나이 | `20` |
| `max_age` | integer | N | 최대 나이 | `80` |
| `page` | integer | N | 페이지 번호 | `1` |
| `size` | integer | N | 페이지당 조회 개수 | `20` |

#### 요청 예시

```http
GET /api/v1/patients?name=김&gender=M&min_age=20&max_age=80&page=1&size=20
Authorization: Bearer {access_token}
```

#### 검색 + 필터 WHERE 조합 원리

환자 목록 조회에서는 전달된 검색/필터 조건만 `WHERE` 조건에 추가한다.

| 조건 | SQLAlchemy 조건 예시 | 설명 |
| --- | --- | --- |
| 이름 검색 | `Patient.name.like(f"%{name}%")` | 이름에 검색어가 포함된 환자 조회 |
| 성별 필터 | `Patient.gender == gender` | 선택한 성별과 일치하는 환자 조회 |
| 최소 나이 | `Patient.age >= min_age` | 최소 나이 이상 환자 조회 |
| 최대 나이 | `Patient.age <= max_age` | 최대 나이 이하 환자 조회 |

예를 들어 `name`과 `gender`만 전달되면 이름 검색 조건과 성별 조건만 적용하고, `min_age`, `max_age`는 `WHERE`에 포함하지 않는다. 이렇게 하면 사용자가 선택한 조건에 따라 동적으로 검색 범위를 조절할 수 있다.

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `200 OK` | 환자 목록 조회 성공 |

```json
{
  "data": [
    {
      "id": 1,
      "name": "김환자",
      "age": 45,
      "gender": "M",
      "phone": "01012345678",
      "created_at": "2026-07-20T15:30:00",
      "updated_at": null
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 1
  }
}
```

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 환자 목록 조회 권한이 없는 경우 |
| `422 Unprocessable Entity` | 쿼리 파라미터 타입 또는 범위가 올바르지 않은 경우 |

### 4-3. 환자 정보 상세 조회

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PTNT-003 |
| Method | `GET` |
| URL | `/api/v1/patients/{patient_id}` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| 설명 | 환자 목록에서 선택한 환자의 기본 정보를 상세 조회한다. |

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `patient_id` | integer | Y | 조회할 환자 고유 ID |

#### 요청 예시

```http
GET /api/v1/patients/1
Authorization: Bearer {access_token}
```

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `200 OK` | 환자 상세 조회 성공 |

```json
{
  "data": {
    "id": 1,
    "name": "김환자",
    "age": 45,
    "gender": "M",
    "phone": "01012345678",
    "created_at": "2026-07-20T15:30:00",
    "updated_at": null
  }
}
```

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 환자 상세 조회 권한이 없는 경우 |
| `404 Not Found` | 해당 `patient_id`의 환자가 존재하지 않는 경우 |
| `422 Unprocessable Entity` | `patient_id` 형식이 올바르지 않은 경우 |

### 4-4. 환자 정보 수정

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PTNT-004 |
| Method | `PATCH` |
| URL | `/api/v1/patients/{patient_id}` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| Content-Type | `application/json` |
| 설명 | 환자 상세 페이지에서 환자의 이름과 연락처를 수정한다. |

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `patient_id` | integer | Y | 수정할 환자 고유 ID |

#### 요청 Body

| 필드 | 타입 | 필수 | 설명 | 제약 조건 |
| --- | --- | --- | --- | --- |
| `name` | string | N | 환자 이름 | 최대 30자 |
| `phone` | string | N | 환자 연락처 | 숫자 11자리 |

수정 가능한 항목은 요구사항에 따라 `name`, `phone`으로 제한한다. `age`, `gender`는 이 API에서 수정하지 않는다.

#### 요청 예시

```json
{
  "name": "김수정",
  "phone": "01098765432"
}
```

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `200 OK` | 환자 정보 수정 성공 |

```json
{
  "data": {
    "id": 1,
    "name": "김수정",
    "age": 45,
    "gender": "M",
    "phone": "01098765432",
    "created_at": "2026-07-20T15:30:00",
    "updated_at": "2026-07-20T16:10:00"
  },
  "message": "환자 정보가 수정되었습니다."
}
```

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `400 Bad Request` | 수정할 필드가 하나도 전달되지 않은 경우 |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 환자 정보 수정 권한이 없는 경우 |
| `404 Not Found` | 해당 `patient_id`의 환자가 존재하지 않는 경우 |
| `422 Unprocessable Entity` | 입력값 형식이 올바르지 않은 경우 |

### 4-5. 환자 정보 삭제

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-PTNT-005 |
| Method | `DELETE` |
| URL | `/api/v1/patients/{patient_id}` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| 설명 | 환자 상세 페이지에서 환자 정보를 삭제한다. 삭제 시 관련 진료기록과 X-Ray 이미지도 함께 삭제된다. |

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `patient_id` | integer | Y | 삭제할 환자 고유 ID |

#### 요청 예시

```http
DELETE /api/v1/patients/1
Authorization: Bearer {access_token}
```

#### Cascade 삭제 구조

환자 삭제 시 관련 데이터가 함께 삭제되도록 DB 관계와 ORM 관계를 cascade로 설계한다.

| 부모 데이터 | 자식 데이터 | 삭제 정책 | 설명 |
| --- | --- | --- | --- |
| `patients` | `medical_records` | `CASCADE` | 환자를 삭제하면 해당 환자의 진료기록도 삭제된다. |
| `medical_records` | `xray_images` | `CASCADE` | 진료기록을 삭제하면 연결된 X-Ray 이미지 데이터도 삭제된다. |
| `medical_records` | `ai_analysis_results` | `CASCADE` | 진료기록을 삭제하면 연결된 AI 분석 결과도 삭제된다. |

서버 로컬 저장소에 저장된 실제 이미지 파일은 DB 레코드 삭제와 별도로 파일 시스템에서도 삭제해야 한다. 따라서 구현 시에는 DB 삭제 트랜잭션과 이미지 파일 삭제 처리 순서를 함께 고려한다.

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `204 No Content` | 환자 및 관련 데이터 삭제 성공 |

응답 본문은 반환하지 않는다.

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 환자 삭제 권한이 없는 경우 |
| `404 Not Found` | 해당 `patient_id`의 환자가 존재하지 않는 경우 |
| `422 Unprocessable Entity` | `patient_id` 형식이 올바르지 않은 경우 |

---

## 5. 진료기록 API

### 5-1. 진료기록 등록

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-MDR-001 |
| Method | `POST` |
| URL | `/api/v1/medical-records` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| Content-Type | `multipart/form-data` |
| 설명 | 환자의 진료정보와 촬영된 흉부 X-Ray 이미지를 함께 등록한다. |

#### 요청 Form Data

| 필드 | 타입 | 필수 | 설명 | 제약 조건 |
| --- | --- | --- | --- | --- |
| `patient_id` | integer | Y | 환자 고유 ID | 존재하는 환자 ID |
| `chart_number` | string | Y | 진료 차트 번호 | 최대 50자, 고유값 |
| `symptoms` | string | Y | 진료된 증상 | 빈 문자열 불가 |
| `shooting_datetime` | datetime | Y | X-Ray 촬영 일시 | ISO 8601 형식 |
| `xray_image` | file | Y | 촬영된 흉부 X-Ray 이미지 | jpg, jpeg, png 등 이미지 파일 |

#### 요청 예시

```http
POST /api/v1/medical-records
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

```text
patient_id=1
chart_number=CHART-20260720-001
symptoms=기침, 고열, 흉부 통증
shooting_datetime=2026-07-20T15:30:00
xray_image=@chest_xray.png
```

#### FastAPI 구현 방식

파일 업로드가 포함되므로 JSON Body가 아니라 `Form()`과 `UploadFile`을 사용한다.

```python
async def create_medical_record(
    patient_id: int = Form(...),
    chart_number: str = Form(...),
    symptoms: str = Form(...),
    shooting_datetime: datetime = Form(...),
    xray_image: UploadFile = File(...),
):
    ...
```

`BaseModel`은 기본적으로 JSON Body를 파싱할 때 사용하고, `UploadFile`은 `multipart/form-data`를 파싱할 때 사용한다. 두 방식은 요청 본문의 인코딩 방식이 다르기 때문에 그대로 섞으면 Swagger UI와 FastAPI 요청 파싱이 기대한 형태로 동작하지 않을 수 있다. 여러 Form 필드를 모델처럼 묶고 싶다면 `as_form` 메서드를 정의하여 Form 값을 Pydantic 모델로 변환하는 방식을 사용할 수 있다.

#### 처리 조건

- `patient_id`에 해당하는 환자가 존재하는지 먼저 확인한다.
- `chart_number`는 중복될 수 없으므로 이미 등록된 차트 번호면 등록을 거부한다.
- 업로드된 X-Ray 이미지는 서버가 실행되는 환경의 로컬 저장소에 저장한다.
- DB에는 실제 파일 자체가 아니라 접근 가능한 경로 또는 URL을 `xray_images.image_url`에 저장한다.
- 진료기록 생성과 X-Ray 이미지 정보 저장은 하나의 트랜잭션으로 처리한다.

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `201 Created` | 진료기록 등록 성공 |

```json
{
  "data": {
    "id": 1,
    "patient_id": 1,
    "chart_number": "CHART-20260720-001",
    "symptoms": "기침, 고열, 흉부 통증",
    "xray_image": {
      "id": 1,
      "image_url": "/uploads/xrays/20260720_153000_chest_xray.png",
      "shooting_datetime": "2026-07-20T15:30:00"
    },
    "created_at": "2026-07-20T15:31:00",
    "updated_at": null
  },
  "message": "진료기록이 등록되었습니다."
}
```

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `400 Bad Request` | 업로드 파일이 이미지 형식이 아니거나 저장에 실패한 경우 |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 진료기록 등록 권한이 없는 경우 |
| `404 Not Found` | 해당 `patient_id`의 환자가 존재하지 않는 경우 |
| `409 Conflict` | 이미 존재하는 `chart_number`인 경우 |
| `422 Unprocessable Entity` | 필수 Form 필드 또는 파일이 누락된 경우 |

### 5-2. 진료기록 목록 조회

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-MDR-002 |
| Method | `GET` |
| URL | `/api/v1/patients/{patient_id}/medical-records` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| 설명 | 환자 상세 페이지에서 해당 환자의 진료기록 목록을 조회한다. |

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `patient_id` | integer | Y | 진료기록 목록을 조회할 환자 고유 ID |

#### Query Parameters

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `page` | integer | N | 1 | 조회할 페이지 번호 |
| `size` | integer | N | 20 | 페이지당 조회 개수 |

#### 요청 예시

```http
GET /api/v1/patients/1/medical-records?page=1&size=20
Authorization: Bearer {access_token}
```

#### selectinload 사용 이유

진료기록 목록에서 X-Ray 이미지 정보를 함께 보여줘야 한다면 `MedicalRecord`를 조회한 뒤 각 진료기록마다 `xray_images`를 다시 조회하는 상황이 생길 수 있다. 이 경우 진료기록이 N개일 때 추가 쿼리가 N번 발생하는 N+1 문제가 생긴다.

이를 줄이기 위해 SQLAlchemy의 `selectinload(MedicalRecord.xray_images)`를 사용하면, 진료기록 목록 조회 쿼리 1번과 관련 X-Ray 이미지 조회 쿼리 1번으로 데이터를 가져올 수 있다.

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `200 OK` | 진료기록 목록 조회 성공 |

```json
{
  "data": [
    {
      "id": 1,
      "chart_number": "CHART-20260720-001",
      "symptoms": "기침, 고열, 흉부 통증",
      "created_at": "2026-07-20T15:31:00"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 1
  }
}
```

목록 화면에서는 요구사항에 따라 증상이 100자를 초과하면 말줄임 형태로 표시할 수 있도록 프론트엔드에서 처리하거나, API에서 `symptoms_summary` 필드를 별도로 제공할 수 있다.

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 진료기록 목록 조회 권한이 없는 경우 |
| `404 Not Found` | 해당 `patient_id`의 환자가 존재하지 않는 경우 |
| `422 Unprocessable Entity` | `patient_id` 또는 쿼리 파라미터 형식이 올바르지 않은 경우 |

### 5-3. 진료기록 상세 조회

| 항목 | 내용 |
| --- | --- |
| 요구사항 ID | REQ-MDR-003 |
| Method | `GET` |
| URL | `/api/v1/medical-records/{record_id}` |
| 인증 | 필요 |
| 권한 | `STAFF`, `ADMIN` |
| 설명 | 선택한 진료기록의 상세 정보와 X-Ray 이미지를 조회한다. |

#### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `record_id` | integer | Y | 조회할 진료기록 고유 ID |

#### 요청 예시

```http
GET /api/v1/medical-records/1
Authorization: Bearer {access_token}
```

#### 성공 응답

| 상태 코드 | 설명 |
| --- | --- |
| `200 OK` | 진료기록 상세 조회 성공 |

```json
{
  "data": {
    "id": 1,
    "patient_id": 1,
    "chart_number": "CHART-20260720-001",
    "symptoms": "기침, 고열, 흉부 통증",
    "xray_images": [
      {
        "id": 1,
        "image_url": "/uploads/xrays/20260720_153000_chest_xray.png",
        "shooting_datetime": "2026-07-20T15:30:00",
        "created_at": "2026-07-20T15:31:00"
      }
    ],
    "created_at": "2026-07-20T15:31:00",
    "updated_at": null
  }
}
```

#### 예외 상황

| 상태 코드 | 발생 조건 |
| --- | --- |
| `401 Unauthorized` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | 진료기록 상세 조회 권한이 없는 경우 |
| `404 Not Found` | 해당 `record_id`의 진료기록이 존재하지 않는 경우 |
| `422 Unprocessable Entity` | `record_id` 형식이 올바르지 않은 경우 |

---

## 6. 에러 응답

### 6-1. 공통 에러 응답 형식

에러 응답은 프론트엔드에서 동일한 방식으로 처리할 수 있도록 아래 형식을 사용한다.

```json
{
  "error": {
    "code": "PATIENT_NOT_FOUND",
    "message": "환자 정보를 찾을 수 없습니다.",
    "detail": null
  }
}
```

### 6-2. 주요 에러 코드

| HTTP 상태 코드 | 에러 코드 | 설명 |
| --- | --- | --- |
| `400 Bad Request` | `INVALID_REQUEST` | 요청은 전달되었지만 비즈니스 처리 조건에 맞지 않는 경우 |
| `400 Bad Request` | `INVALID_FILE_TYPE` | 업로드한 파일이 허용된 이미지 형식이 아닌 경우 |
| `401 Unauthorized` | `UNAUTHORIZED` | access token이 없거나 유효하지 않은 경우 |
| `403 Forbidden` | `FORBIDDEN` | 로그인은 되었지만 해당 API를 호출할 권한이 없는 경우 |
| `404 Not Found` | `PATIENT_NOT_FOUND` | 요청한 환자가 존재하지 않는 경우 |
| `404 Not Found` | `MEDICAL_RECORD_NOT_FOUND` | 요청한 진료기록이 존재하지 않는 경우 |
| `409 Conflict` | `DUPLICATED_CHART_NUMBER` | 이미 등록된 진료 차트 번호인 경우 |
| `422 Unprocessable Entity` | `VALIDATION_ERROR` | 필수값 누락, 타입 불일치, 형식 오류가 발생한 경우 |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | 서버 내부 오류가 발생한 경우 |

### 6-3. 에러 응답 예시

#### 인증 실패

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "로그인이 필요합니다.",
    "detail": null
  }
}
```

#### 권한 부족

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "해당 기능에 접근할 권한이 없습니다.",
    "detail": null
  }
}
```

#### 환자 없음

```json
{
  "error": {
    "code": "PATIENT_NOT_FOUND",
    "message": "환자 정보를 찾을 수 없습니다.",
    "detail": {
      "patient_id": 1
    }
  }
}
```

---

## 7. 비기능 요구사항

### 7-1. API 응답 성능

| 요구사항 ID | 대상 | 기준 |
| --- | --- | --- |
| NFR-PTNT-001 | 환자 관리 API | 모든 요청은 최대 3초 이내에 처리하고 응답한다. |
| NFR-MDR-001 | 진료기록 API | 모든 요청은 최대 3초 이내에 처리하고 응답한다. |

성능 기준을 만족하기 위해 목록 조회 API에는 페이지네이션을 적용하고, 관계 데이터가 필요한 조회에는 `selectinload`를 사용하여 N+1 문제를 줄인다.

### 7-2. 파일 저장 정책

- X-Ray 이미지는 서버가 실행되는 환경의 로컬 저장소에 저장한다.
- DB에는 파일 바이너리가 아니라 파일 경로 또는 URL을 저장한다.
- 허용 확장자는 `jpg`, `jpeg`, `png` 등 이미지 파일로 제한한다.
- 파일명 충돌을 피하기 위해 저장 시점에는 UUID 또는 날짜 기반의 고유 파일명을 사용한다.
- 환자 또는 진료기록 삭제 시 DB 레코드뿐 아니라 실제 이미지 파일 삭제도 함께 고려한다.

### 7-3. 데이터 무결성

- 존재하지 않는 환자 ID로 진료기록을 등록할 수 없다.
- `chart_number`는 중복 등록할 수 없다.
- 환자 삭제 시 관련 진료기록, X-Ray 이미지, AI 분석 결과는 cascade 정책에 따라 함께 삭제된다.
- 진료기록과 X-Ray 이미지 저장은 하나의 트랜잭션으로 처리하여 일부 데이터만 저장되는 상황을 방지한다.

### 7-4. 보안

- 모든 환자/진료기록 API는 JWT 인증을 필요로 한다.
- `PENDING` 권한 사용자는 환자/진료기록 API에 접근할 수 없다.
- 권한이 부족한 사용자의 요청은 `403 Forbidden`으로 차단한다.
- 업로드 파일은 확장자와 MIME type을 확인하여 이미지 파일만 허용한다.
- 서버에 저장되는 파일명은 사용자가 업로드한 원본 파일명을 그대로 사용하지 않는다.

---

## 8. 완료 체크리스트

- [x] 요구사항 기반 환자 관리 API 명세 작성
- [x] 요구사항 기반 진료기록 API 명세 작성
- [x] 요청/응답 필드 정의
- [x] 에러 응답 정의
- [x] 비기능 요구사항 반영
