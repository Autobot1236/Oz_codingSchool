# 5일차 환자 관리·진료기록 API 설계

## 1. 목적과 범위

이 문서는 5일차 요구사항 정의서의 환자(Patient) 및 진료기록(MedicalRecord) 기능을 구현하기 위한 REST API 계약이다. 모든 API는 기존 User/Auth API와 동일하게 `/api/v1` 접두사를 사용한다.

- 대상 요구사항: `REQ-PTNT-001` ~ `REQ-PTNT-005`, `REQ-MDR-001` ~ `REQ-MDR-003`
- 이번 범위: 환자 CRUD 5개, 진료기록 등록·목록·상세 조회 3개(총 8개)
- 범위 제외: AI 폐렴 예측 및 분석 결과 조회 API, 진료기록 수정·삭제 API

## 2. 공통 규칙

### 인증과 권한

모든 API는 아래 헤더로 로그인한 활성 사용자를 확인한다.

```http
Authorization: Bearer <access_token>
```

| 구분 | 허용 사용자 | 근거 |
| --- | --- | --- |
| 환자·진료기록 조회 | 로그인한 활성 사용자 | 개발진·의료 실무진·연구진 모두 조회 가능 |
| 환자 등록·수정·삭제 | `department == MEDICAL`인 사용자 | 요구사항의 “사내 의료인 역할을 가진 유저” |
| 진료기록 등록 | `department == MEDICAL`인 사용자 | 요구사항의 “사내 의료인 역할을 가진 유저” |

`Role`은 `PENDING`, `STAFF`, `ADMIN` 계정 권한을 뜻하고 의료진 식별 값이 아니므로, 이번 도메인 권한은 기존 `User.department`의 `MEDICAL` 값으로 판단한다. 인증되지 않았거나 토큰이 유효하지 않으면 `401`, 로그인했지만 의료진 권한이 없으면 `403`을 반환한다.

### 표기와 응답 원칙

- 요청·응답 필드는 `snake_case`를 사용한다.
- 성별은 기존 enum 코드 `M`, `F`만 허용한다.
- 날짜와 시간은 ISO 8601 문자열로 반환한다. 예: `2026-07-22T10:30:00`
- 등록은 `201 Created`, 조회·수정은 `200 OK`, 삭제는 응답 본문 없는 `204 No Content`를 사용한다.
- FastAPI 검증 실패는 `422 Unprocessable Entity`, 존재하지 않는 리소스는 `404 Not Found`를 사용한다.
- 목록 API의 기본 페이지는 `page=1`, 기본 크기는 `size=10`, 최대 크기는 `size=100`이다.

### 현재 모델과 API 필드 매핑

| API 필드 | 현재 DB 모델 필드 | 비고 |
| --- | --- | --- |
| `phone_number` | `Patient.phone` | 외부 계약은 기존 화면과 User/Auth 용어 규칙에 맞춘다. Repository/Service에서 매핑한다. |
| `patient_id` | `MedicalRecord.patient_id` | 진료기록 등록에서는 URL 경로의 값을 사용하며 Form으로 중복 전송하지 않는다. |
| `xray_image_url` | `XrayImage.image_url` | 이번 요구사항은 기록당 X-Ray 1장을 등록한다. 모델은 향후 다중 이미지 확장을 위해 목록 관계를 유지한다. |
| `shooting_datetime` | `XrayImage.shooting_datetime` | 요구사항에 별도 입력값이 없으므로 서버가 업로드 시각(UTC)을 기록한다. |

## 3. API 목록과 요구사항 매핑

| 요구사항 | 메서드 | 경로 | 인증/권한 | 설명 |
| --- | --- | --- | --- | --- |
| `REQ-PTNT-001` | `POST` | `/api/v1/patients` | 의료진 | 환자 등록 |
| `REQ-PTNT-002` | `GET` | `/api/v1/patients` | 로그인 사용자 | 이름 검색, 성별·나이 범위 필터를 포함한 목록 조회 |
| `REQ-PTNT-003` | `GET` | `/api/v1/patients/{patient_id}` | 로그인 사용자 | 환자 상세 조회 |
| `REQ-PTNT-004` | `PATCH` | `/api/v1/patients/{patient_id}` | 의료진 | 이름·연락처 수정 |
| `REQ-PTNT-005` | `DELETE` | `/api/v1/patients/{patient_id}` | 의료진 | 환자와 연관 진료기록·X-Ray 영구 삭제 |
| `REQ-MDR-001` | `POST` | `/api/v1/patients/{patient_id}/medical-records` | 의료진 | X-Ray 파일을 포함한 진료기록 등록 |
| `REQ-MDR-002` | `GET` | `/api/v1/patients/{patient_id}/medical-records` | 로그인 사용자 | 특정 환자의 진료기록 목록 조회 |
| `REQ-MDR-003` | `GET` | `/api/v1/medical-records/{record_id}` | 로그인 사용자 | 진료기록 상세 조회 |

## 4. 환자 API 명세

### 4.1 환자 정보 등록 — `POST /api/v1/patients`

의료진이 환자 정보를 등록한다.

**요청**

```json
{
  "name": "김환자",
  "age": 42,
  "gender": "F",
  "phone_number": "01012345678"
}
```

| 필드 | 타입 | 필수 | 검증 규칙 |
| --- | --- | --- | --- |
| `name` | string | 예 | 공백 제거 후 1~30자 |
| `age` | integer | 예 | 0~150 |
| `gender` | string | 예 | `M`, `F` 중 하나 |
| `phone_number` | string | 예 | 숫자 10~11자리, 하이픈 없이 저장 |

**성공 응답 — `201 Created`**

```json
{
  "id": 1,
  "name": "김환자",
  "age": 42,
  "gender": "F",
  "phone_number": "01012345678",
  "created_at": "2026-07-22T10:30:00",
  "updated_at": null
}
```

### 4.2 환자 목록 조회 — `GET /api/v1/patients`

로그인 사용자가 환자를 이름으로 검색하고 성별·나이 범위를 조합해 조회한다. 지정하지 않은 필터는 적용하지 않는다.

| 쿼리 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `name` | string | 아니오 | 이름 부분 일치 검색 |
| `gender` | string | 아니오 | `M` 또는 `F` |
| `min_age` | integer | 아니오 | 0 이상 최소 나이 |
| `max_age` | integer | 아니오 | 150 이하 최대 나이 |
| `page` | integer | 아니오 | 기본값 `1`, 1 이상 |
| `size` | integer | 아니오 | 기본값 `10`, 1~100 |

`min_age`가 `max_age`보다 크면 `422`를 반환한다.

**성공 응답 — `200 OK`**

```json
{
  "patients": [
    {
      "id": 1,
      "name": "김환자",
      "age": 42,
      "gender": "F",
      "phone_number": "01012345678",
      "created_at": "2026-07-22T10:30:00",
      "updated_at": null
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

### 4.3 환자 상세 조회 — `GET /api/v1/patients/{patient_id}`

로그인 사용자가 환자 한 명의 상세 정보를 조회한다.

| 경로 파라미터 | 타입 | 설명 |
| --- | --- | --- |
| `patient_id` | integer | 조회할 환자 고유 ID |

**성공 응답 — `200 OK`**

```json
{
  "id": 1,
  "name": "김환자",
  "age": 42,
  "gender": "F",
  "phone_number": "01012345678",
  "created_at": "2026-07-22T10:30:00",
  "updated_at": null
}
```

존재하지 않는 `patient_id`는 `404`와 `{"detail": "patient_not_found"}`를 반환한다.

### 4.4 환자 정보 수정 — `PATCH /api/v1/patients/{patient_id}`

의료진이 환자의 이름 또는 연락처만 부분 수정한다. 나이와 성별은 이 API에서 수정할 수 없다.

**요청**

```json
{
  "name": "김새이름",
  "phone_number": "01098765432"
}
```

| 필드 | 타입 | 필수 | 검증 규칙 |
| --- | --- | --- | --- |
| `name` | string | 아니오 | 공백 제거 후 1~30자 |
| `phone_number` | string | 아니오 | 숫자 10~11자리 |

- 두 필드 중 하나 이상을 보내야 하며, 빈 JSON 객체는 `400`과 `{"detail": "update_fields_required"}`를 반환한다.
- 허용하지 않은 필드 또는 `null` 값은 `422`를 반환한다.
- 성공 시 수정된 환자 정보를 `200 OK`로 반환한다.

### 4.5 환자 정보 삭제 — `DELETE /api/v1/patients/{patient_id}`

의료진이 환자와 연결된 진료기록, X-Ray DB 데이터 및 서버 로컬 이미지 파일을 영구 삭제한다.

- 성공: `204 No Content`
- 대상 환자가 없으면: `404`와 `{"detail": "patient_not_found"}`
- 삭제 확인 모달과 경고 문구는 프론트엔드에서 제공하며, API는 별도 확인용 플래그를 요구하지 않는다.

## 5. 진료기록 API 명세

### 5.1 진료기록 등록 — `POST /api/v1/patients/{patient_id}/medical-records`

의료진이 특정 환자에게 진료기록과 흉부 X-Ray 이미지 1장을 등록한다. 파일을 포함하므로 JSON이 아닌 `multipart/form-data`를 사용한다.

**헤더**

```http
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**경로 파라미터**

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `patient_id` | integer | 진료기록을 등록할 환자 고유 ID |

**Form 필드**

| 필드 | 타입 | 필수 | 검증 규칙 |
| --- | --- | --- | --- |
| `chart_number` | string | 예 | 공백 제거 후 1~50자, 전체 진료기록에서 고유 |
| `symptoms` | string | 예 | 공백 제거 후 1자 이상 |
| `xray_image` | file | 예 | `image/jpeg`, `image/png`만 허용, 최대 10 MiB |

`patient_id`는 URL로 전달하므로 Form 본문에 넣지 않는다. 브라우저에서는 `FormData`를 사용하고, `Content-Type` 헤더의 boundary는 브라우저가 자동으로 설정하도록 직접 지정하지 않는다.

**성공 응답 — `201 Created`**

```json
{
  "id": 10,
  "patient_id": 1,
  "chart_number": "C-2026-0001",
  "symptoms": "기침과 발열이 3일간 지속됨",
  "xray_image_url": "/media/xray/8a6f1c2e.png",
  "shooting_datetime": "2026-07-22T10:45:00",
  "created_at": "2026-07-22T10:45:00"
}
```

| 상황 | 상태 | 응답 `detail` |
| --- | --- | --- |
| 대상 환자 없음 | `404` | `patient_not_found` |
| 차트 번호 중복 | `409` | `chart_number_already_exists` |
| 필수 Form 필드 누락·형식 오류·허용하지 않는 이미지 | `422` | FastAPI 검증 오류 또는 `invalid_xray_image` |
| 의료진 권한 없음 | `403` | `medical_department_required` |

### 5.2 환자별 진료기록 목록 조회 — `GET /api/v1/patients/{patient_id}/medical-records`

로그인 사용자가 환자 상세 화면에서 해당 환자의 진료기록을 조회한다. 목록 성능을 위해 증상은 100자를 초과하면 앞 100자 뒤에 `…`을 붙여 반환한다. 전체 증상은 상세 조회에서 확인한다.

| 쿼리 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `page` | integer | 아니오 | 기본값 `1`, 1 이상 |
| `size` | integer | 아니오 | 기본값 `10`, 1~100 |

**성공 응답 — `200 OK`**

```json
{
  "records": [
    {
      "id": 10,
      "chart_number": "C-2026-0001",
      "symptoms": "기침과 발열이 3일간 지속됨",
      "created_at": "2026-07-22T10:45:00"
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

환자가 존재하지 않으면 빈 목록 대신 `404`와 `{"detail": "patient_not_found"}`를 반환한다.

### 5.3 진료기록 상세 조회 — `GET /api/v1/medical-records/{record_id}`

로그인 사용자가 차트 번호, 전체 증상, X-Ray 이미지와 생성일시를 조회한다.

**성공 응답 — `200 OK`**

```json
{
  "id": 10,
  "patient_id": 1,
  "chart_number": "C-2026-0001",
  "symptoms": "기침과 발열이 3일간 지속됨",
  "xray_image_url": "/media/xray/8a6f1c2e.png",
  "shooting_datetime": "2026-07-22T10:45:00",
  "created_at": "2026-07-22T10:45:00"
}
```

존재하지 않는 `record_id`는 `404`와 `{"detail": "medical_record_not_found"}`를 반환한다.

## 6. 파일 저장과 삭제 정책

### X-Ray 저장

1. Service가 업로드 파일의 MIME 타입·크기·실제 이미지 여부를 검증한다.
2. 파일명은 사용자 입력 파일명을 그대로 사용하지 않고 UUID 기반 이름으로 생성한다.
3. 파일은 서버 로컬 `./media/xray/` 하위에 저장하고, 외부 응답에는 `/media/xray/<파일명>` 형식의 URL만 노출한다.
4. `MedicalRecord`와 `XrayImage`를 하나의 DB 트랜잭션으로 생성한다. `XrayImage.uploader_id`에는 현재 로그인한 의료진 ID를, `shooting_datetime`에는 서버 기록 시각을 저장한다.
5. DB 저장에 실패하면 방금 저장한 로컬 파일을 정리한다.

### 환자 삭제

`Patient → MedicalRecord → XrayImage`는 이미 DB 외래 키 `ON DELETE CASCADE`와 SQLAlchemy 관계의 `delete-orphan`으로 연결되어 있다. Service는 삭제 전에 연관 X-Ray 파일 경로를 조회하고, DB 삭제가 성공한 뒤 `./media/xray/` 안의 해당 파일만 삭제한다.

- `ai_analysis_results`도 진료기록 삭제에 연쇄 삭제된다.
- 파일 경로는 반드시 `media/xray` 루트 하위인지 확인한 뒤 삭제하여 경로 조작을 막는다.
- 파일 삭제 실패는 서버 로그와 재시도 대상에 남긴다. DB 삭제가 성공했으므로 API 응답은 `204`이며, 운영 시 정리 작업으로 고아 파일을 제거한다.

## 7. 구현 계층과 프론트엔드 연동 기준

기존 프로젝트의 계층 분리를 유지한다.

| 계층 | 책임 |
| --- | --- |
| `app/apis/patients.py`, `app/apis/medical_records.py` | 라우팅, HTTP 상태 코드, 의존성 주입, `response_model` 선언 |
| `app/schemas/patient.py`, `app/schemas/medical_record.py` | 요청·응답 스키마와 Pydantic 검증 |
| `app/services/patient_service.py`, `app/services/medical_record_service.py` | 권한 확인, 검색·필터, 트랜잭션, 파일 저장·삭제 정책 |
| `app/repositories/patient_repository.py`, `app/repositories/medical_record_repository.py` | `AsyncSession`을 이용한 DB 조회·저장·삭제 |

모든 DB I/O는 `AsyncSession`과 `await`를 사용한다. API 계층에는 SQLAlchemy 질의나 파일 시스템 처리 로직을 직접 두지 않는다.

현재 정적 화면을 위 계약에 맞출 때 필요한 변경점은 다음과 같다.

- `static/apis.js`의 진료기록 등록 경로를 `/medical-records`에서 `/patients/{patient_id}/medical-records`로 변경한다.
- `static/pages.js`의 `FormData`에서 `patient_id`를 제거하고 URL 경로로만 전달한다.
- 환자·진료기록 목록 응답은 각각 `patients`, `records` 배열과 페이징 메타데이터를 반환하므로 화면은 해당 배열을 사용한다.
- 환자 응답 연락처 필드는 모두 `phone_number`로 통일한다.

## 8. 검증과 완료 기준

### 주요 테스트 케이스

| 구분 | 확인 항목 | 기대 결과 |
| --- | --- | --- |
| 환자 등록 | 의료진이 유효한 JSON 전송 | `201` 및 생성된 환자 반환 |
| 환자 등록 | 개발·연구 부서 사용자 | `403` |
| 환자 목록 | 이름·성별·나이 범위를 함께 지정 | 모든 조건을 만족하는 환자만 반환 |
| 환자 수정 | 빈 JSON 객체 전송 | `400` |
| 환자 삭제 | 진료기록·X-Ray가 있는 환자 삭제 | DB 연관 데이터와 로컬 파일이 함께 삭제 |
| 기록 등록 | JPEG/PNG 파일과 Form 필드 전송 | `201`, 로컬 파일 저장 및 URL 반환 |
| 기록 등록 | 중복 `chart_number` | `409` |
| 기록 목록 | 100자 초과 증상 | 앞 100자와 `…`만 반환 |
| 기록 상세 | 존재하지 않는 ID | `404` |
| 공통 | 인증 헤더 없음 또는 유효하지 않은 토큰 | `401` |

Swagger UI(`/docs`)에서 8개 엔드포인트의 정상·권한 실패·검증 실패·리소스 없음 시나리오를 모두 확인한다. 각 API는 일반적인 개발 환경에서 최대 3초 이내 응답해야 한다.

## 9. 참고 자료

- [환자 관리 및 진료기록 API 설계 및 작성](https://app.notion.com/p/767638e5d636835dbb08015992729a8d)
- [5일차 - 진료기록 사용자 요구사항 정의서](https://app.notion.com/p/9e3638e5d636836b8bbb8164cb806184)
- `docs/4일차_USER_API_설계.md`
- `app/models/patient.py`, `app/models/medical_record.py`, `app/models/xray_image.py`
- FastAPI [폼 및 파일 요청](https://fastapi.tiangolo.com/ko/tutorial/request-forms-and-files/)

## 10. 역할별 API 구현 분담안

5명 기준 권장 분담안이다. 모든 팀원은 최소 1개 API의 API·Service·Repository·테스트 중 담당 범위를 끝까지 구현하고, 병합 전 Swagger UI로 정상·실패 시나리오를 확인한다.

| 담당 | 담당 API | 주 담당 계층 | 배정 근거 |
| --- | --- | --- | --- |
| 이희진 | `GET /api/v1/patients` | Query Schema, Patient Repository | 이름 검색·성별·나이 범위 필터·페이지네이션의 공통 조회 기준을 담당한다. |
| 이수인 | `GET /api/v1/patients/{patient_id}`<br>`GET /api/v1/medical-records/{record_id}` | API, Response Schema | 인증된 상세 조회와 환자·진료기록의 `404` 응답 계약을 담당한다. |
| 안상균 | `POST /api/v1/patients`<br>`DELETE /api/v1/patients/{patient_id}` | Patient Service, Repository | 환자 생성과 연관 진료기록·X-Ray 데이터의 삭제 정책 및 트랜잭션을 담당한다. |
| 양준혁 | `PATCH /api/v1/patients/{patient_id}`<br>`POST /api/v1/patients/{patient_id}/medical-records` | MedicalRecord Service, File Storage | 부분 수정 검증과 `multipart/form-data` X-Ray 업로드·파일 정리 흐름을 담당한다. |
| 홍주(프론트·통합 담당) | `GET /api/v1/patients/{patient_id}/medical-records` | API 연동, 목록 Response Schema | 증상 100자 말줄임·페이지네이션 응답을 환자 상세 화면에 연결하고 통합 테스트를 담당한다. |

### 공통 작업 순서

1. **공통 계약 확정:** `PatientCreate`, `PatientUpdate`, 목록 응답, 진료기록 응답 Schema와 의료진 권한 의존성을 먼저 합의한다.
2. **환자 API 구현:** 등록·목록·상세·수정·삭제를 먼저 완성해 진료기록 API가 참조할 환자 데이터를 확보한다.
3. **진료기록 API 구현:** 파일 저장 경로, DB 트랜잭션, 실패 시 파일 정리 규칙을 적용한다.
4. **통합 검증:** Swagger UI에서 각 담당자가 정상 요청과 `401`, `403`, `404`, `409`, `422` 시나리오를 확인한다.

### 병합 전 책임

- 담당자는 자신이 수정한 API의 정상·실패 테스트를 추가한다.
- 파일 업로드와 환자 삭제 변경은 로컬 파일이 실제로 생성·삭제되는지 함께 확인한다.
- 프론트·통합 담당자는 API 경로와 응답 필드가 문서 계약과 같은지 확인한다.
