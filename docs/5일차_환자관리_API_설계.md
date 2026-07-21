# 5일차 환자 관리 API 설계

## 0. 문서 개요

| 항목 | 내용 |
| --- | --- |
| 대상 도메인 | Patient(환자), MedicalRecord(진료기록), XrayImage(X-Ray 이미지) |
| API Base URL | `/api/v1` |
| 인증 방식 | `Authorization: Bearer <access_token>` |
| 공통 응답 형식 | JSON (단, X-Ray 업로드 요청은 `multipart/form-data`) |
| 근거 요구사항 | `REQ-PTNT-001`~`005`, `REQ-MDR-001`~`003`, `NFR-PTNT-001`, `NFR-MDR-001` |
| 참고 구현 | `app/models/patient.py`, `app/models/medical_record.py`, `app/models/xray_image.py`, `app/models/enums.py` |

> 이 문서는 제공된 요구사항을 우선 적용하고, 구현에 필요한 미명시 정책은 일반적인 REST API 및 의료정보 보호 원칙에 따라 보완한 설계안입니다.

---

## 1. 공통 정책

### 1.1 액터 및 접근 권한

| 액터 | 조건 | 허용 범위 |
| --- | --- | --- |
| 의료 실무진 | `role=STAFF`이며 `department=MEDICAL` | 환자 등록, 환자 조회·수정·삭제, 진료기록 등록·조회 |
| 개발진 | `role=STAFF`이며 `department=DEV` | 환자 조회·수정·삭제, 진료기록 조회 |
| 연구진 | `role=STAFF`이며 `department=RESEARCH` | 환자 조회·수정·삭제, 진료기록 조회 |
| 관리자 | `role=ADMIN` | 전체 기능 허용 |
| 권한 대기자 | `role=PENDING` | 환자 및 진료기록 API 접근 불가 |

> `REQ-PTNT-004`, `REQ-PTNT-005`에 따라 개발진·의료 실무진·연구진 모두에게 수정·삭제를 허용합니다. 다만 모든 변경·삭제 작업은 감사 로그에 기록합니다.

### 1.2 공통 Headers

| Key | Value | 필수 | 설명 |
| --- | --- | --- | --- |
| Authorization | `Bearer <access_token>` | Y | 로그인 사용자 인증 토큰 |
| Content-Type | `application/json` | 요청별 | JSON 요청 본문이 있는 경우 사용 |

### 1.3 공통 오류 응답

```json
{
  "detail": "오류 메시지"
}
```

| HTTP 상태 | 발생 조건 |
| --- | --- |
| `400 Bad Request` | 요청값 또는 파일 형식이 올바르지 않음 |
| `401 Unauthorized` | 인증 정보가 없거나 유효하지 않음 |
| `403 Forbidden` | 해당 작업에 필요한 역할 또는 부서 권한이 없음 |
| `404 Not Found` | 환자 또는 진료기록을 찾을 수 없음 |
| `409 Conflict` | 진료 차트 넘버 등 고유값이 중복됨 |
| `422 Unprocessable Entity` | 필수 필드 누락 또는 필드 유효성 검증 실패 |
| `500 Internal Server Error` | 서버 내부 처리 실패 |

### 1.4 목록 조회 정책

- 목록 API는 `page`와 `size`를 사용하는 페이지네이션을 적용합니다.
- 기본값은 `page=1`, `size=10`이며 `size`는 1~100만 허용합니다.
- 기본 정렬은 최신 생성순(`created_at DESC`)입니다.
- 검색어 앞뒤 공백은 제거하고, 이름 검색은 부분 일치로 처리합니다.

---

## 2. API 목록

| 요구사항 ID | API 이름 | Method | Endpoint |
| --- | --- | --- | --- |
| REQ-PTNT-001 | 환자 정보 등록 | `POST` | `/api/v1/patients` |
| REQ-PTNT-002 | 환자 목록 조회 | `GET` | `/api/v1/patients` |
| REQ-PTNT-003 | 환자 정보 상세 조회 | `GET` | `/api/v1/patients/{patient_id}` |
| REQ-PTNT-004 | 환자 정보 수정 | `PATCH` | `/api/v1/patients/{patient_id}` |
| REQ-PTNT-005 | 환자 정보 삭제 | `DELETE` | `/api/v1/patients/{patient_id}` |
| REQ-MDR-001 | 진료기록 등록 | `POST` | `/api/v1/patients/{patient_id}/medical-records` |
| REQ-MDR-002 | 환자별 진료기록 목록 조회 | `GET` | `/api/v1/patients/{patient_id}/medical-records` |
| REQ-MDR-003 | 진료기록 상세 조회 | `GET` | `/api/v1/patients/{patient_id}/medical-records/{record_id}` |
| REQ-MDR-003 | X-Ray 이미지 조회 | `GET` | `/api/v1/xray-images/{image_id}/content` |

---

## 3. 환자 정보 등록 API

### 3.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 등록 API |
| 설명 | 의료 실무진 또는 관리자가 환자 정보를 등록 |
| Endpoint | `/api/v1/patients` |
| Method | `POST` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 관리자 |

### 3.2 요청(Request)

```json
{
  "name": "김환자",
  "birth_date": "1961-03-15",
  "gender": "M",
  "phone": "01012345678"
}
```

| 필드명 | 타입 | 필수 | 제약 조건 | 설명 |
| --- | --- | --- | --- | --- |
| name | string | Y | 1~30자 | 환자 이름 |
| birth_date | string(date) | Y | 미래 날짜 불가, 만 150세 이내 | 환자 생년월일. 프론트엔드에서 만 나이로 변환하여 표시 |
| gender | string | Y | `M` 또는 `F` | 환자 성별 |
| phone | string | Y | 입력 시 하이픈 허용, 저장 시 숫자 11자리 | 휴대폰 번호 |

### 3.3 응답(Response)

#### 성공: `201 Created`

```json
{
  "id": 1,
  "name": "김환자",
  "birth_date": "1961-03-15",
  "gender": "M",
  "phone": "01012345678",
  "created_at": "2026-07-21T10:00:00",
  "updated_at": null
}
```

#### 주요 실패

- `403 Forbidden`: 의료 실무진 또는 관리자 권한이 아님
- `422 Unprocessable Entity`: 필수값 누락 또는 형식 오류

### 3.4 비고

- 현재 모델상 `gender`는 nullable이지만 요구사항상 필수이므로 API에서는 필수값으로 검증합니다.
- 요구사항의 나이 항목은 정확한 갱신을 위해 백엔드에서 `birth_date`로 저장합니다. 프론트엔드는 생년월일을 기준으로 조회 시점의 만 나이를 계산해 표시합니다.
- 연락처는 입력값의 하이픈과 공백을 제거한 숫자 11자리로 정규화해 저장합니다.
- 보호자와 환자가 동일 연락처를 사용할 수 있으므로 연락처 중복을 허용합니다.

---

## 4. 환자 목록 조회 API

### 4.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 목록 조회 API |
| 설명 | 로그인한 사내 구성원이 환자 목록을 검색·필터링하여 조회 |
| Endpoint | `/api/v1/patients` |
| Method | `GET` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 4.2 요청(Request)

#### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| name | string | N | - | 환자 이름 검색어 |
| gender | string | N | - | `M` 또는 `F` |
| min_age | integer | N | - | 최소 나이(포함) |
| max_age | integer | N | - | 최대 나이(포함) |
| page | integer | N | 1 | 페이지 번호 |
| size | integer | N | 10 | 페이지당 항목 수 |

요청 예시:

```http
GET /api/v1/patients?name=김&gender=M&min_age=60&max_age=69&page=1&size=10
```

`min_age`, `max_age`는 화면에서 나이를 기준으로 전달하지만, 백엔드는 요청일을 기준으로 생년월일 범위로 변환하여 조회합니다.

### 4.3 응답(Response)

#### 성공: `200 OK`

```json
{
  "patients": [
    {
      "id": 1,
      "name": "김환자",
      "birth_date": "1961-03-15",
      "gender": "M",
      "phone": "01012345678",
      "created_at": "2026-07-21T10:00:00",
      "updated_at": null
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| patients | array | 환자 목록 |
| patients[].id | integer | 환자 고유 ID |
| patients[].name | string | 이름 |
| patients[].birth_date | string(date) | 생년월일. 프론트엔드에서 만 나이로 계산하여 표시 |
| patients[].gender | string | 성별 |
| patients[].phone | string | 연락처 |
| patients[].created_at | datetime | 생성일시 |
| patients[].updated_at | datetime/null | 수정일시 |
| page | integer | 현재 페이지 |
| size | integer | 페이지당 항목 수 |
| total | integer | 검색 조건에 맞는 전체 항목 수 |

#### 주요 실패

- `400 Bad Request`: 최소 나이가 최대 나이보다 큼
- `403 Forbidden`: 접근 가능한 내부 사용자 권한이 아님

---

## 5. 환자 정보 상세 조회 API

### 5.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 상세 조회 API |
| 설명 | 환자 고유 ID로 환자 상세 정보를 조회 |
| Endpoint | `/api/v1/patients/{patient_id}` |
| Method | `GET` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 5.2 Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 환자 고유 ID |

### 5.3 응답(Response)

#### 성공: `200 OK`

```json
{
  "id": 1,
  "name": "김환자",
  "birth_date": "1961-03-15",
  "gender": "M",
  "phone": "01012345678",
  "created_at": "2026-07-21T10:00:00",
  "updated_at": null
}
```

#### 주요 실패

- `404 Not Found`: 환자를 찾을 수 없음

---

## 6. 환자 정보 수정 API

### 6.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 수정 API |
| 설명 | 환자의 이름 또는 연락처를 부분 수정 |
| Endpoint | `/api/v1/patients/{patient_id}` |
| Method | `PATCH` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 6.2 요청(Request)

```json
{
  "name": "김수정",
  "phone": "01098765432"
}
```

| 필드명 | 타입 | 필수 | 제약 조건 | 설명 |
| --- | --- | --- | --- | --- |
| name | string | N | 1~30자 | 변경할 이름 |
| phone | string | N | 숫자 11자리 | 변경할 휴대폰 번호 |

### 6.3 응답(Response)

#### 성공: `200 OK`

```json
{
  "id": 1,
  "name": "김수정",
  "birth_date": "1961-03-15",
  "gender": "M",
  "phone": "01098765432",
  "created_at": "2026-07-21T10:00:00",
  "updated_at": "2026-07-21T11:00:00"
}
```

#### 주요 실패

- `400 Bad Request`: 수정할 필드가 없음
- `404 Not Found`: 환자를 찾을 수 없음
- `422 Unprocessable Entity`: 허용되지 않은 필드 또는 잘못된 형식

### 6.4 비고

- 요구사항에 따라 수정 가능 필드는 `name`, `phone`으로 제한합니다.
- 요구사항에 명시되지 않은 생년월일과 성별은 이 API에서 수정할 수 없습니다.

---

## 7. 환자 정보 삭제 API

### 7.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자 정보 삭제 API |
| 설명 | 환자 및 연결된 진료기록·X-Ray 이미지 데이터를 영구 삭제 |
| Endpoint | `/api/v1/patients/{patient_id}` |
| Method | `DELETE` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 7.2 Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 삭제할 환자 고유 ID |

### 7.3 응답(Response)

#### 성공: `204 No Content`

응답 본문을 반환하지 않습니다.

#### 주요 실패

- `404 Not Found`: 환자를 찾을 수 없음

### 7.4 처리 조건

- 클라이언트는 삭제 API 호출 전에 영구 삭제 및 연관 데이터 삭제 안내와 사용자 확인 절차를 제공합니다.
- 환자 삭제 시 DB의 `ON DELETE CASCADE`에 따라 진료기록, X-Ray 이미지, AI 분석 결과가 함께 삭제됩니다.
- 로컬 저장소의 실제 X-Ray 이미지 파일도 함께 제거합니다. 파일을 먼저 격리 디렉터리로 이동하고 DB 트랜잭션을 커밋한 뒤 제거하며, 실패 시 재처리 작업과 오류 로그를 남깁니다.
- 삭제는 복구할 수 없는 hard delete입니다.

---

## 8. 진료기록 등록 API

### 8.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 등록 API |
| 설명 | 선택한 환자에게 진료 정보와 흉부 X-Ray 이미지를 등록 |
| Endpoint | `/api/v1/patients/{patient_id}/medical-records` |
| Method | `POST` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 관리자 |
| Content-Type | `multipart/form-data` |

### 8.2 Path Parameter

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 진료기록을 등록할 환자 고유 ID |

### 8.3 요청(Request)

```http
Content-Type: multipart/form-data

chart_number=CHART-20260721-001
symptoms=기침과 발열이 3일간 지속됨
xray_image=<binary file>
```

| 필드명 | 타입 | 필수 | 제약 조건 | 설명 |
| --- | --- | --- | --- | --- |
| chart_number | string | Y | 최대 50자, 고유값 | 진료 차트 넘버 |
| symptoms | string | Y | 빈 문자열 불가 | 진료된 증상 |
| xray_image | binary | Y | JPEG 또는 PNG, 최대 10MB, 1개 | 촬영된 흉부 X-Ray 이미지 |

### 8.4 응답(Response)

#### 성공: `201 Created`

```json
{
  "id": 10,
  "patient_id": 1,
  "chart_number": "CHART-20260721-001",
  "symptoms": "기침과 발열이 3일간 지속됨",
  "xray_images": [
    {
      "id": 100,
      "image_url": "/api/v1/xray-images/100/content",
      "shooting_datetime": "2026-07-21T09:30:00",
      "created_at": "2026-07-21T10:00:00"
    }
  ],
  "created_at": "2026-07-21T10:00:00",
  "updated_at": null
}
```

#### 주요 실패

- `400 Bad Request`: 지원하지 않는 이미지 형식 또는 용량 초과
- `404 Not Found`: 환자를 찾을 수 없음
- `409 Conflict`: 진료 차트 넘버 중복
- `422 Unprocessable Entity`: 필수값 누락

### 8.5 처리 조건

- 업로드 파일은 서버 실행 환경의 `uploads/xrays/YYYY/MM/` 아래에 저장합니다.
- DB에는 실제 파일이 아니라 접근 경로(`image_url`)를 저장합니다.
- 원본 파일명은 저장 경로에 사용하지 않고, 서버가 UUID 기반 파일명을 생성합니다.
- 확장자뿐 아니라 실제 MIME 타입과 파일 시그니처를 함께 검증합니다.
- 현재 요구사항은 단일 X-Ray 이미지를 필수로 하므로 요청당 이미지 1개만 허용합니다.
- `shooting_datetime`은 요구사항의 입력 항목이 아니므로 서버가 업로드 시각으로 자동 설정합니다.
- DB 저장 실패 시 이미 저장된 파일을 제거하는 보상 처리가 필요합니다.
- 업로드 미리보기는 프론트엔드 기능이며, API는 업로드 가능한 파일 검증과 저장을 담당합니다.

---

## 9. 환자별 진료기록 목록 조회 API

### 9.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 환자별 진료기록 목록 조회 API |
| 설명 | 특정 환자의 진료기록을 목록으로 조회 |
| Endpoint | `/api/v1/patients/{patient_id}/medical-records` |
| Method | `GET` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 9.2 요청(Request)

| 파라미터명 | 위치 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- | --- |
| patient_id | Path | integer | Y | - | 환자 고유 ID |
| page | Query | integer | N | 1 | 페이지 번호 |
| size | Query | integer | N | 10 | 페이지당 항목 수 |

### 9.3 응답(Response)

#### 성공: `200 OK`

```json
{
  "medical_records": [
    {
      "id": 10,
      "chart_number": "CHART-20260721-001",
      "symptoms": "기침과 발열이 3일간 지속됨",
      "created_at": "2026-07-21T10:00:00"
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| medical_records | array | 진료기록 목록 |
| medical_records[].id | integer | 진료기록 ID |
| medical_records[].chart_number | string | 진료 차트 넘버 |
| medical_records[].symptoms | string | 증상. UI에서 100자 초과 시 말줄임 표시 |
| medical_records[].created_at | datetime | 생성일시 |
| page | integer | 현재 페이지 |
| size | integer | 페이지당 항목 수 |
| total | integer | 전체 진료기록 수 |

#### 주요 실패

- `404 Not Found`: 환자를 찾을 수 없음

### 9.4 비고

- `REQ-MDR-002`의 구분은 비기능으로 기재되어 있으나 내용상 기능 요구사항에 해당합니다.
- 100자 말줄임은 표시 정책입니다. 원문 훼손을 피하기 위해 API는 전체 증상을 반환하고 UI에서 생략 표시하는 방식을 권장합니다.

---

## 10. 진료기록 상세 조회 API

### 10.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | 진료기록 상세 조회 API |
| 설명 | 특정 환자의 진료기록과 X-Ray 이미지를 상세 조회 |
| Endpoint | `/api/v1/patients/{patient_id}/medical-records/{record_id}` |
| Method | `GET` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 10.2 Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| patient_id | integer | Y | 환자 고유 ID |
| record_id | integer | Y | 진료기록 ID |

### 10.3 응답(Response)

#### 성공: `200 OK`

```json
{
  "id": 10,
  "patient_id": 1,
  "chart_number": "CHART-20260721-001",
  "symptoms": "기침과 발열이 3일간 지속됨",
  "xray_images": [
    {
      "id": 100,
      "image_url": "/api/v1/xray-images/100/content",
      "shooting_datetime": "2026-07-21T09:30:00",
      "created_at": "2026-07-21T10:00:00"
    }
  ],
  "created_at": "2026-07-21T10:00:00",
  "updated_at": null
}
```

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| id | integer | 진료기록 ID |
| patient_id | integer | 환자 고유 ID |
| chart_number | string | 차트 넘버 |
| symptoms | string | 증상 |
| xray_images | array | 연결된 흉부 X-Ray 이미지 목록 |
| created_at | datetime | 생성일시 |
| updated_at | datetime/null | 수정일시 |

#### 주요 실패

- `404 Not Found`: 환자 또는 해당 환자에게 속한 진료기록을 찾을 수 없음

### 10.4 처리 조건

- `record_id`가 존재하더라도 URL의 `patient_id`와 연결되지 않은 경우 `404 Not Found`로 처리하여 다른 환자의 진료기록 노출을 방지합니다.

---

## 11. X-Ray 이미지 조회 API

### 11.1 API 개요

| 항목 | 내용 |
| --- | --- |
| API 이름 | X-Ray 이미지 조회 API |
| 설명 | 인증 및 권한 검증 후 저장된 X-Ray 이미지 원본을 반환 |
| Endpoint | `/api/v1/xray-images/{image_id}/content` |
| Method | `GET` |
| 인증 필요 여부 | Y |
| 권한 | 의료 실무진, 개발진, 연구진, 관리자 |

### 11.2 응답(Response)

- 성공: `200 OK`, 저장된 이미지의 실제 `Content-Type`과 바이너리 본문 반환
- 실패: 이미지 또는 연결된 진료기록이 없으면 `404 Not Found`
- 브라우저 캐시와 중간 캐시에 의료 이미지가 남지 않도록 `Cache-Control: private, no-store`를 적용합니다.
- 로컬 저장 디렉터리를 정적 공개 경로로 노출하지 않습니다. 상세 조회 응답의 `image_url`은 이 인증 API 주소를 반환합니다.

---

## 12. 비기능 요구사항

| 요구사항 ID | 항목 | 기준 | 검증 방법 |
| --- | --- | --- | --- |
| NFR-PTNT-001 | 환자 API 성능 | 정상적인 부하 조건에서 최대 3초 이내 응답 | API 응답시간 테스트 |
| NFR-MDR-001 | 진료기록 API 성능 | 정상적인 부하 조건에서 최대 3초 이내 응답 | API 응답시간 테스트 |

- 원문에는 “모든 유저 API”로 기재되어 있으나 문맥상 각각 환자 API와 진료기록 API를 의미하는 것으로 해석했습니다.
- 성능 기준은 서버가 요청 전체를 수신한 시점부터 응답을 완료할 때까지 95백분위 응답시간 3초 이내로 측정합니다. 네트워크 파일 전송 시간은 제외하고 서버의 파일 검증·저장 시간은 포함합니다.
- 환자 연락처와 진료기록은 민감정보이므로 HTTPS, 접근 권한 검증, 로그 내 개인정보 마스킹 정책이 필요합니다.
- 환자 정보 조회·등록·수정·삭제와 진료기록 및 이미지 조회·등록은 사용자 ID, 대상 ID, 작업, 결과, 시각을 감사 로그로 남깁니다. 증상·연락처·이미지 원문과 인증 토큰은 로그에 기록하지 않습니다.

---

## 13. 데이터 모델 매핑

### 13.1 Patient

| API 필드 | DB 필드 | DB 제약 |
| --- | --- | --- |
| id | `patients.id` | PK, BigInteger |
| name | `patients.name` | VARCHAR(30), NOT NULL |
| birth_date | `patients.birth_date` | Date, NOT NULL. 기존 `patients.age`를 대체하도록 마이그레이션 필요 |
| gender | `patients.gender` | Enum(`M`, `F`), 현재 nullable |
| phone | `patients.phone` | VARCHAR(11), NOT NULL |
| created_at | `patients.created_at` | NOT NULL |
| updated_at | `patients.updated_at` | nullable |

### 13.2 MedicalRecord / XrayImage

| API 필드 | DB 필드 | DB 제약 |
| --- | --- | --- |
| patient_id | `medical_records.patient_id` | FK → `patients.id`, ON DELETE CASCADE |
| chart_number | `medical_records.chart_number` | VARCHAR(50), UNIQUE, NOT NULL |
| symptoms | `medical_records.symptoms` | TEXT, NOT NULL |
| image_url | `xray_images.image_url` | VARCHAR(2048), NOT NULL |
| shooting_datetime | `xray_images.shooting_datetime` | DateTime, NOT NULL |
| uploader_id | `xray_images.uploader_id` | FK → `users.id`, ON DELETE SET NULL |

---

## 14. 설계 결정 및 잔여 위험

### 14.1 미명시 항목에 적용한 기본 정책

| 항목 | 적용 정책 |
| --- | --- |
| 나이 | 백엔드는 `birth_date`를 저장·응답하고, 프론트엔드는 조회 시점의 만 나이를 계산하여 표시 |
| 연락처 | 하이픈·공백 제거 후 숫자 11자리 저장, 중복 허용 |
| 수정·삭제 권한 | 요구사항대로 STAFF 전체 부서와 ADMIN에 허용, 감사 로그 필수 |
| X-Ray 파일 | JPEG/PNG, 최대 10MB, 요청당 1개 |
| 촬영일시 | 별도 입력 없이 업로드 시각으로 자동 설정 |
| 저장 경로 | `uploads/xrays/YYYY/MM/{uuid}.{ext}` |
| 이미지 접근 | 정적 공개 금지, 인증된 이미지 조회 API 사용 |
| 환자 삭제 | 진료기록·X-Ray DB 행·AI 분석 결과·실제 이미지 파일 영구 삭제 |
| 목록 조회 | `page=1`, `size=10`, 최대 100개, 최신 생성순 |
| 성능 | 요청 수신 후 서버 처리시간의 95백분위 3초 이내 |
| 감사 로그 | 사용자·대상·작업·결과·시각 기록, 민감정보 원문 제외 |

### 14.2 구현 시 주의할 위험

1. 현재 `patients.gender`가 nullable이므로 요구사항의 필수 입력 조건과 일치하도록 DB 마이그레이션에서 `NOT NULL` 적용이 필요합니다.
2. 현재 DB의 `patients.age`를 `patients.birth_date`로 변경하는 마이그레이션이 필요합니다. 기존 나이 데이터만으로 정확한 생년월일을 복원할 수 없으므로 기존 데이터가 있다면 별도 보정 기준이 필요합니다.
3. 개발진과 연구진의 환자 수정·삭제 권한은 요구사항을 그대로 적용했지만 최소 권한 원칙에는 맞지 않습니다. 운영 적용 전 개인정보 접근권한 책임자의 승인이 필요합니다.
4. 감사 로그 저장소와 보관 기간은 현재 데이터 모델에 없습니다. 운영 전 별도 테이블과 보관 정책을 추가해야 합니다.
