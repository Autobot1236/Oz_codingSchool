# 6일차 폐렴 예측 AI API 설계

## 1. 목적과 범위

이 문서는 진료기록에 저장된 흉부 X-Ray 이미지와 Simple CNN 모델을 이용해 폐렴 예측 결과를 생성·조회하기 위한 API 계약을 정의한다.

- 대상 요구사항: `REQ-PRED-001`, `REQ-PRED-002`
- 비기능 요구사항: `NFR-PRED-001`, `NFR-PRED-002`
- 모델 구현 위치: `worker/model.py`
- 기본 모델 식별자: `simple-cnn-state-dict-v1`
- 추론 프레임워크: PyTorch CPU
- 이번 범위:
  - 진료기록 단위 폐렴 예측 실행 또는 저장 결과 재사용
  - 진료기록 단위 예측 결과 목록 조회
  - Simple CNN Worker와 API Service 사이의 입출력 계약
  - 모델 평가 및 API 성능 검증 기준
- 범위 제외:
  - 의료진의 최종 진단 자동 확정
  - 모델 학습·재학습 API
  - AI 예측 결과 수정·삭제 API
  - DICOM 원본 처리

> **안전 원칙:** AI 결과는 의료진의 판단을 보조하는 정보이며 확정 진단을 대체하지 않는다. 화면에는 모델명, 예측 시각, 신뢰도와 함께 이 안내를 표시한다.

---

## 2. 요구사항 해석과 설계 결정

### 2.0 통합 계약 결정

초기 역할 가이드의 `/predict`, `/analyses` 경로는 담당자 간 계약을 병합하기 전 템플릿이다. DB·캐시 Service와 완료된 화면 호출을 대조한 결과, 최종 통합 경로는 두 기능 모두 `/ai-predictions`로 확정한다.

- 실행: `POST /api/v1/medical-records/{record_id}/ai-predictions`
- 목록: `GET /api/v1/medical-records/{record_id}/ai-predictions`
- 목록 envelope: `{ "predictions": [...], "page": 1, "size": 10, "total": 0 }`

### 2.1 요구사항 매핑

| 요구사항 | 설계 반영 |
| --- | --- |
| `REQ-PRED-001` | `POST /api/v1/medical-records/{record_id}/ai-predictions` |
| 동일 기록·동일 모델 결과 재사용 | `record_id + ai_model` 고유 제약 및 캐시 우선 조회 |
| 저장된 X-Ray 사용 | `MedicalRecord.xray_images`에서 현재 기록의 X-Ray 경로 조회 |
| `REQ-PRED-002` | `GET /api/v1/medical-records/{record_id}/ai-predictions` |
| 목록 필드 | ID, 폐렴 여부, Confidence, Heatmap URL, 예측 시각, 모델명 |
| `NFR-PRED-001` | 독립 테스트 세트에서 Recall 최소 `0.90`, Accuracy 보조 기준 |
| `NFR-PRED-002` | 모델 사전 로딩과 캐시 사용, API 응답시간 계측 |

### 2.2 용어 통일

요구사항의 `Hitmap Image URL`은 일반적인 명칭과 현재 모델 필드에 맞춰 API에서는 `heatmap_url`로 통일한다.

### 2.3 Confidence 표현

- API의 `confidence`는 Worker 반환값과 동일하게 `0.0~100.0` 범위의 백분율로 반환한다.
- Confidence는 `softmax` 결과 중 `argmax`로 선택된 클래스의 확률이다.
- `is_pneumonia=true`이면 폐렴 클래스 신뢰도이고, `false`이면 정상 클래스 신뢰도이다.
- 현재 모델은 별도 임계값을 사용하지 않고 두 클래스 중 확률이 높은 클래스를 선택한다.
- UI는 전달받은 값을 그대로 `%` 단위로 표시하며 다시 100을 곱하지 않는다.

### 2.4 권한

기존 인증 정책과 맞춰 다음 조건을 모두 만족해야 한다.

1. 유효한 Access Token을 가진 활성 사용자
2. `Role.STAFF` 또는 `Role.ADMIN`
3. 부서는 `MEDICAL`, `DEV`, `RESEARCH` 중 하나

현재 `Department` enum이 위 세 부서만 포함하므로 실제 권한 차단 기준은 `Role.PENDING` 여부가 된다.

| 상황 | 상태 코드 | 응답 `detail` |
| --- | --- | --- |
| 토큰 없음·만료·위조 | `401` | 기존 인증 모듈의 메시지 사용 |
| `Role.PENDING` | `403` | `prediction_access_denied` |
| 비활성 사용자 | `401` | 기존 인증 모듈의 메시지 사용 |

---

## 3. 전체 처리 구조

```text
Client
  │
  ├─ POST /medical-records/{id}/ai-predictions
  │
FastAPI API
  │  인증·권한·경로 파라미터 처리
Prediction Service
  │
  ├─ MedicalRecord / XrayImage 조회
  ├─ 기존 (record_id, ai_model) 결과 조회
  │    └─ 있으면 즉시 반환
  │
  └─ 없으면 worker/model.py 추론 호출
       ├─ 이미지 전처리
       ├─ Simple CNN 추론
       └─ (is_pneumonia, confidence_percent) 반환
  │
Prediction Repository
  │  결과 저장 또는 동시 요청 시 기존 결과 재조회
MySQL
```

### 계층별 책임

| 계층 | 예정 파일 | 책임 |
| --- | --- | --- |
| API | `app/apis/medical_records.py` | 라우팅, 인증 의존성, 상태 코드, 응답 모델 |
| Schema | `app/schemas/medical_record.py` | 요청·응답 및 목록 페이지네이션 검증 |
| Service | `app/services/prediction_service.py` | 권한, 캐시, X-Ray 파일 확인, Worker 호출, 예외 변환 |
| Repository | `app/repositories/prediction_repository.py` | 예측 결과 조회·목록·저장 |
| Worker | `worker/model.py` | 모델 로딩, 전처리, Simple CNN 추론 |
| DB Model | `app/models/ai_analysis_result.py` | 예측 결과 영속화 |

모든 DB I/O는 `AsyncSession`과 `await`를 사용한다. PyTorch CPU 추론은 동기·CPU 집약 작업이므로 FastAPI 이벤트 루프에서 직접 실행하지 않고 thread pool 또는 별도 Worker 실행 영역으로 분리한다.

---

## 4. Worker 모델 계약

`worker/model.py`의 내부 CNN 구조는 모델 담당자가 구현한다. API 계층은 내부 레이어를 알지 않고 아래 공개 계약에만 의존한다.

### 4.1 공개 상수

```python
MODEL_NAME = "simple-cnn-state-dict-v1"
IMAGE_SIZE = 128
MODEL_PATH = Path(__file__).resolve().parent / "models" / "model_state_dict.pth"
PNEUMONIA_CLASS_INDEX = 1
```

- `MODEL_NAME`이 바뀌면 새로운 모델로 간주한다.
- 모델 구조, 가중치, 전처리 또는 클래스 순서가 바뀌어 기존 결과와 직접 비교할 수 없으면 모델 버전을 올린다.
- 운영 중 같은 `MODEL_NAME`의 의미를 바꾸지 않는다.
- 모델 클래스 매핑은 `index 0 = normal`, `index 1 = pneumonia`로 확정하며 `PNEUMONIA_CLASS_INDEX = 1`을 사용한다.

### 4.2 출력 계약

현재 공개 함수:

```python
def predict_xray(image_path: Path) -> tuple[bool, float]:
    ...
```

- 첫 번째 값: `is_pneumonia`
- 두 번째 값: 선택된 클래스의 `confidence_percent`, 범위 `0.0~100.0`
- 현재 Worker는 Heatmap을 생성하지 않는다.

### 4.3 입력·출력 규칙

| 항목 | 규칙 |
| --- | --- |
| 입력 | 서버 내부 X-Ray 이미지 절대 경로를 담은 `pathlib.Path` |
| 허용 파일 | 진료기록 등록 단계에서 검증된 JPEG 또는 PNG |
| 크기 | Pillow `LANCZOS`로 `128 × 128` 변환 |
| 채널 | Grayscale 1채널 |
| 정규화 | `[0, 255] → [0, 1]` |
| 텐서 형태 | `(1, 1, 128, 128)` |
| 분류 | 2개 logit에 `softmax`, 가장 높은 클래스를 `argmax`로 선택 |
| Confidence | 선택된 클래스 확률 × 100, 소수 둘째 자리 반올림 |
| Heatmap | 현재 미지원, API에서는 `null` |
| 이미지 예외 | 디코딩 실패 시 `ValueError` |
| 모델 예외 | 의존성·파일·가중치 로딩 실패 시 `RuntimeError` |

학습과 API 추론의 전처리가 달라지면 성능이 재현되지 않으므로 Grayscale, 128×128, `[0, 1]` 정규화를 변경하지 않는다. PyTorch `softmax`는 클래스 점수를 합이 1인 확률 값으로 변환하며, 현재 Worker는 선택된 값에 100을 곱해 백분율로 반환한다.

### 4.4 모델 로딩

- API 요청마다 모델과 가중치를 다시 로드하지 않는다.
- `load_model()`은 `@lru_cache(maxsize=1)`로 최초 요청 시 한 번 로드하고 프로세스 메모리에 유지한다.
- 모델은 CPU에 로드하고 `eval()` 모드로 전환한다.
- 추론은 `torch.inference_mode()` 안에서 실행한다.
- state dict는 `torch.load(..., map_location="cpu", weights_only=True)`로 로드한다.
- 최초 로딩 실패 시 서버 로그에 원인을 남기고 API는 `503 model_unavailable`을 반환한다.
- 현재 모델 경로와 이름은 `worker/model.py` 상수로 고정되어 있다.

현재 모델 파일:

```text
worker/models/model_state_dict.pth
```

`weights_only=True`는 전체 Python 객체를 역직렬화하는 대신 state dict에 필요한 타입으로 로딩 범위를 제한한다. 모델 파일은 신뢰된 프로젝트 저장소의 파일만 사용한다.

---

## 5. 데이터 모델과 마이그레이션

### 5.1 현재 모델

현재 `AIAnalysisResult`는 다음 필드를 가진다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | BigInteger | 예측 결과 ID |
| `record_id` | BigInteger, FK | 진료기록 ID |
| `is_pneumonia` | Boolean | 폐렴 예측 여부 |
| `confidence` | Numeric(5, 2) | 예측 신뢰도 |
| `heatmap_url` | String(255) | Heatmap URL |
| `ai_model` | String(50) | 모델 식별자 |
| `created_at` | DateTime | 예측 수행 시각 |
| `updated_at` | DateTime nullable | 수정 시각 |

### 5.2 필수 변경

현재 모델에는 요구사항과 충돌하는 부분이 있으므로 별도 Alembic migration이 필요하다.

1. `heatmap_url`을 nullable로 변경
   - 요구사항에서 Heatmap은 선택사항이다.
   - Python 타입도 `Mapped[str | None]`로 변경한다.
2. `record_id + ai_model` 복합 고유 제약 추가
   - 같은 진료기록과 같은 모델 결과가 두 번 저장되는 것을 DB 수준에서 방지한다.
3. 조회 성능을 위한 인덱스 추가
   - 결과 목록: `(record_id, created_at)`

권장 제약 및 인덱스:

```python
__table_args__ = (
    UniqueConstraint(
        "record_id",
        "ai_model",
        name="uq_ai_analysis_results_record_model",
    ),
    Index(
        "ix_ai_analysis_results_record_created_at",
        "record_id",
        "created_at",
    ),
)
```

### 5.3 Confidence 정밀도

현재 Worker는 Confidence를 `0.00~100.00` 백분율로 소수 둘째 자리까지 반환한다. `Numeric(5, 2)`는 최대 `999.99`까지 저장할 수 있으므로 현재 출력 계약을 그대로 저장할 수 있다.

- API와 DB의 Confidence 계약: `0.00~100.00`
- Service는 저장 전 유한값과 범위를 검증한다.
- 현재 모델 계약에서는 Confidence 컬럼의 타입 변경이 필요하지 않다.

### 5.4 향후 고려사항

현재 캐시 키는 요구사항대로 `record_id + ai_model`이다. 향후 한 진료기록에 X-Ray가 여러 장 추가되거나 기존 이미지가 교체될 수 있다면 `xray_image_id` 또는 이미지 해시를 결과 테이블에 추가해야 한다.

---

## 6. API 목록

| 요구사항 | 메서드 | 경로 | 설명 |
| --- | --- | --- | --- |
| `REQ-PRED-001` | `POST` | `/api/v1/medical-records/{record_id}/ai-predictions` | 예측 실행 또는 캐시 결과 반환 |
| `REQ-PRED-002` | `GET` | `/api/v1/medical-records/{record_id}/ai-predictions` | 예측 결과 목록 조회 |

### 6.1 공통 오류 계약

| 상태 | `detail` | 발생 조건 | 프론트 안내 |
| ---: | --- | --- | --- |
| `401` | 기존 인증 모듈 메시지 | Access Token 없음·만료·위조 또는 비활성 사용자 | 로그인 화면으로 이동하거나 재로그인 안내 |
| `403` | `prediction_access_denied` | `Role.PENDING` 사용자의 예측 실행·목록 접근 | 관리자 승인 후 이용 가능 안내 |
| `404` | `medical_record_not_found` | `record_id`에 해당하는 진료기록 없음 | 진료기록을 찾을 수 없음 안내 |
| `404` | `xray_image_not_found` | 예측에 사용할 X-Ray DB 정보 또는 파일 없음 | X-Ray 등록 상태 확인 안내 |
| `422` | `invalid_xray_image` | 저장된 X-Ray 파일을 디코딩할 수 없음 | X-Ray 파일을 다시 등록하도록 안내 |
| `422` | FastAPI 검증 오류 | 잘못된 `record_id`, `page`, `size` | 입력값 확인 안내 |
| `503` | `model_unavailable` | 모델 의존성·파일·가중치 로딩 실패 | 잠시 후 재시도 안내 |
| `500` | `prediction_failed` | 추론 또는 결과 저장 중 예상하지 못한 실패 | 일시적 오류 및 재시도 안내 |

오류 `detail`은 하나의 문자열이 하나의 의미만 갖도록 유지하며 내부 경로·모델 파일명·stack trace는 응답에 포함하지 않는다.

---

## 7. 폐렴 예측 실행 API

### `POST /api/v1/medical-records/{record_id}/ai-predictions`

진료기록에 저장된 X-Ray로 기본 모델의 폐렴 예측을 수행한다. 요청 본문은 없다.

### 요청

```http
POST /api/v1/medical-records/10/ai-predictions
Authorization: Bearer <access_token>
```

| 경로 파라미터 | 타입 | 설명 |
| --- | --- | --- |
| `record_id` | integer | 예측할 진료기록 ID |

### 성공 응답 — `200 OK`

신규 추론과 캐시 반환 모두 동일한 응답 계약과 `200`을 사용한다. 프론트엔드는 처리 경로와 무관하게 같은 방식으로 결과를 표시한다.

```json
{
  "id": 101,
  "record_id": 10,
  "is_pneumonia": true,
  "confidence": 94.0,
  "heatmap_url": null,
  "ai_model": "simple-cnn-state-dict-v1",
  "created_at": "2026-07-27T10:30:00",
  "cached": false
}
```

캐시 결과이면 `cached`만 `true`가 된다.

### 처리 순서

1. Access Token과 사용자 활성 상태를 확인한다.
2. `Role.STAFF` 또는 `Role.ADMIN`인지 확인한다.
3. `record_id`의 진료기록을 조회한다.
4. `MODEL_NAME`과 `record_id`로 기존 예측 결과를 먼저 조회한다.
5. 기존 결과가 있으면 Worker를 호출하지 않고 `cached=true`로 반환한다.
6. 기존 결과가 없으면 진료기록의 X-Ray를 조회한다.
7. DB URL을 안전한 로컬 경로로 변환하고 `media/xray` 하위인지 확인한다.
8. `worker.model.predict_xray(Path)`를 thread pool 또는 Worker에서 실행한다.
9. 출력 범위와 유한값을 검증한다.
10. 현재 모델은 Heatmap을 생성하지 않으므로 `heatmap_url=None`으로 저장한다.
11. `AIAnalysisResult`를 저장하고 commit한다.
12. 동시 요청으로 고유 제약 충돌이 발생하면 rollback 후 기존 결과를 다시 조회해 `cached=true`로 반환한다.

### X-Ray 선택 규칙

현재 진료기록 등록 API는 기록당 X-Ray 1장을 저장하므로 해당 이미지를 사용한다.

- X-Ray가 없으면 `404 xray_image_not_found`
- 예상과 달리 여러 장이면 `created_at`이 가장 오래된 최초 등록 이미지를 사용한다.
- 향후 다중 이미지 예측을 지원할 때는 API와 캐시 키를 별도로 변경한다.

### 실패 응답

| 상황 | 상태 | 응답 `detail` |
| --- | --- | --- |
| 인증 실패 | `401` | 기존 인증 응답 |
| 권한 없음 | `403` | `prediction_access_denied` |
| 진료기록 없음 | `404` | `medical_record_not_found` |
| X-Ray DB 정보 없음 | `404` | `xray_image_not_found` |
| X-Ray 파일 누락·손상 | `422` | `invalid_xray_image` |
| 모델 로딩 불가 | `503` | `model_unavailable` |
| 추론 실패 | `500` | `prediction_failed` |
| 제한시간 초과 | `504` | `prediction_timeout` |

내부 파일 경로, 스택 트레이스와 모델 파일 경로는 응답에 노출하지 않는다.

---

## 8. 폐렴 예측 결과 목록 API

### `GET /api/v1/medical-records/{record_id}/ai-predictions`

한 진료기록에서 수행된 모델별 예측 결과를 최신순으로 조회한다.

### 요청

```http
GET /api/v1/medical-records/10/ai-predictions?page=1&size=10
Authorization: Bearer <access_token>
```

| 쿼리 파라미터 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `page` | integer | 아니오 | 기본값 1, 1 이상 |
| `size` | integer | 아니오 | 기본값 10, 1~100 |

### 성공 응답 — `200 OK`

```json
{
  "predictions": [
    {
      "id": 101,
      "record_id": 10,
      "is_pneumonia": true,
      "confidence": 94.0,
      "heatmap_url": null,
      "created_at": "2026-07-27T10:30:00",
      "ai_model": "simple-cnn-state-dict-v1"
    }
  ],
  "page": 1,
  "size": 10,
  "total": 1
}
```

- 정렬: `created_at DESC`, 동일 시각이면 `id DESC`
- Heatmap을 생성하지 않은 결과의 `heatmap_url`은 `null`
- 결과가 없으면 `predictions=[]`, `total=0`
- 진료기록 자체가 없으면 `404 medical_record_not_found`

---

## 9. Schema 설계

권장 Pydantic Schema:

```python
class PredictionListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)


class PredictionItem(BaseModel):
    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float = Field(ge=0.0, le=100.0)
    heatmap_url: str | None
    ai_model: str
    created_at: datetime


class PredictionResponse(PredictionItem):
    cached: bool


class PredictionListResponse(BaseModel):
    predictions: list[PredictionItem]
    page: int
    size: int
    total: int
```

---

## 10. Repository 설계

권장 함수:

```python
async def get_prediction_by_record_and_model(
    session: AsyncSession,
    record_id: int,
    ai_model: str,
) -> AIAnalysisResult | None:
    ...


async def list_predictions(
    session: AsyncSession,
    record_id: int,
    page: int,
    size: int,
) -> tuple[list[AIAnalysisResult], int]:
    ...


def add_prediction(
    session: AsyncSession,
    prediction: AIAnalysisResult,
) -> None:
    ...
```

- Service가 commit과 rollback을 담당한다.
- 목록과 전체 개수 쿼리에 동일한 `record_id` 조건을 사용한다.
- 캐시 조회는 `(record_id, ai_model)` 고유 인덱스를 사용한다.

---

## 11. 동시성·캐시·트랜잭션

### 캐시 기준

```text
cache_key = (record_id, ai_model)
```

API 메모리 캐시가 아니라 DB의 `AIAnalysisResult`를 영속 캐시로 사용한다. 서버 재시작 후에도 결과를 재사용할 수 있다.

### 동시 요청

두 요청이 동시에 기존 결과를 찾지 못하면 둘 다 추론할 수 있다. 최종 중복 저장은 DB 고유 제약으로 방지한다.

1. 두 요청 모두 캐시 miss
2. 각각 추론 수행
3. 먼저 저장한 요청 성공
4. 나중 요청은 `IntegrityError`
5. 나중 요청 rollback
6. 저장된 결과 재조회 후 `cached=true` 반환

DB 중복은 막을 수 있지만 추론 중복까지 완전히 막지는 못한다. 추론 비용이 커지면 추후 분산 잠금 또는 작업 큐를 도입한다.

---

## 12. 성능 설계

### 목표

- 모든 예측·조회 API 응답시간: 3초 이내
- 측정 기준: 서버 처리시간 p95
- 캐시 hit는 DB 조회만 수행하므로 3초보다 충분히 짧아야 한다.

### 적용 항목

1. Simple CNN 모델과 가중치를 최초 추론 요청에서 1회 로드한 뒤 프로세스 메모리에 유지한다.
2. `lru_cache`로 로드된 모델을 재사용하고 요청마다 모델을 생성하거나 가중치를 다시 읽지 않는다.
3. 추론 전 이미지 읽기·리사이즈 시간을 함께 측정한다.
4. PyTorch CPU 추론을 FastAPI 이벤트 루프에서 직접 수행하지 않는다.
5. `(record_id, ai_model)` 인덱스로 캐시 조회를 최적화한다.
6. 처리시간을 `cache_lookup_ms`, `preprocess_ms`, `inference_ms`, `save_ms`, `total_ms`로 나눠 기록한다.
7. 캐시 hit 여부와 모델명은 기록하되 환자 개인정보와 이미지 원본은 로그에 남기지 않는다.

### 제한사항

Simple CNN을 사용한다는 사실만으로 3초 응답을 보장할 수는 없다. CPU/GPU, 모델 크기, 이미지 크기와 동시 요청 수를 포함한 실제 환경에서 부하 테스트가 필요하다.

in-process thread pool은 실행 중인 PyTorch 연산을 안전하게 강제 종료하기 어렵다. 엄격한 3초 제한이 필요하면 추론을 별도 프로세스 또는 작업 Worker로 분리하고 호출 timeout을 적용한다.

---

## 13. 모델 평가 기준

### 혼동행렬 정의

| 구분 | 의미 |
| --- | --- |
| TP | 실제 폐렴을 폐렴으로 예측 |
| FP | 실제 정상을 폐렴으로 예측 |
| FN | 실제 폐렴을 정상으로 예측 |
| TN | 실제 정상을 정상으로 예측 |

### 지표

```text
Recall = TP / (TP + FN)
Accuracy = (TP + TN) / (TP + FP + FN + TN)
```

| 지표 | 완료 기준 | 용도 |
| --- | --- | --- |
| Recall | 최소 `0.90`, 목표 `0.90~0.95 이상` | 폐렴 환자 누락 최소화 |
| Accuracy | 목표 `0.80~0.90 이상` | 전체 예측 정확도의 보조 지표 |

### 평가 원칙

1. 환자 단위로 train/validation/test를 분리해 같은 환자의 이미지가 여러 세트에 섞이지 않게 한다.
2. 분류 임계값은 validation 세트에서 결정한다.
3. test 세트는 임계값 확정 이후 최종 평가에 한 번 사용한다.
4. Recall과 Accuracy뿐 아니라 혼동행렬, Precision, Specificity, ROC-AUC도 함께 기록한다.
5. 데이터 출처, 환자군, 촬영 장비 또는 전처리가 달라지면 성능 저하 가능성을 확인한다.
6. 모델 버전별 평가 결과와 학습 데이터 버전을 보존한다.

> **중요:** `Recall ≥ 0.90`은 API 코드나 Simple CNN 구조만으로 보장되는 값이 아니다. 독립 테스트 세트에서 측정해 통과한 모델만 배포 대상으로 승인해야 한다.

---

## 14. 보안·개인정보·의료 안전

- API 응답에 서버의 절대 파일 경로를 포함하지 않는다.
- DB의 `image_url`을 로컬 경로로 바꿀 때 `media/xray` 루트 하위인지 검증한다.
- 사용자 입력으로 모델 파일 경로나 X-Ray 경로를 직접 받지 않는다.
- 로그에는 환자 이름, 연락처, 원본 이미지와 Access Token을 남기지 않는다.
- AI 결과 화면에 모델 버전, 예측 시각, Confidence와 보조 정보 안내를 표시한다.
- Confidence가 높더라도 확정 진단 문구를 사용하지 않는다.
- 모델 성능은 배포 후에도 모델 버전과 입력 데이터 변화에 따라 모니터링한다.

의료 AI/ML은 데이터·모델의 반복적 특성과 실제 사용 환경을 포함한 전체 수명주기 관리가 필요하다. FDA와 국제 규제기관의 GMLP 원칙도 임상적으로 관련된 조건에서의 시험, 사용자에게 필요한 정보 제공, 인간-AI 팀 성능과 배포 후 모니터링을 강조한다.

---

## 15. 오류 처리와 운영 로그

### 오류 응답 원칙

- 예상 가능한 도메인 오류는 정해진 `detail` 코드로 반환한다.
- 예상하지 못한 Worker·파일 시스템·DB 오류는 내부 로그에 stack trace를 남기되 클라이언트에는 일반화된 메시지를 반환한다.
- DB 저장 실패 시 session을 rollback한다.
- Heatmap 파일 저장 후 DB 저장이 실패했다면 생성한 Heatmap 파일을 정리한다.

### 필수 로그 필드

| 필드 | 설명 |
| --- | --- |
| `request_id` | 요청 추적 ID |
| `record_id` | 진료기록 ID |
| `ai_model` | 모델 버전 |
| `cached` | 캐시 사용 여부 |
| `total_ms` | 전체 처리시간 |
| `inference_ms` | 추론 처리시간 |
| `result` | success 또는 오류 코드 |

---

## 16. 테스트 계획

### API·Service

| 테스트 | 기대 결과 |
| --- | --- |
| 유효한 STAFF/ADMIN 요청, 캐시 없음 | Worker 1회 호출, 결과 저장, `200`, `cached=false` |
| 동일 기록·동일 모델 재요청 | Worker 미호출, 저장 결과 반환, `cached=true` |
| 동일 기록·새 모델 버전 요청 | 신규 추론 및 별도 결과 저장 |
| 인증 헤더 없음 | `401` |
| `Role.PENDING` 요청 | `403 prediction_access_denied` |
| 존재하지 않는 진료기록 | `404 medical_record_not_found` |
| X-Ray가 없는 진료기록 | `404 xray_image_not_found` |
| Worker 모델 로딩 실패 | `503 model_unavailable` |
| Worker 추론 실패 | `500 prediction_failed` |
| 동시 저장 고유 제약 충돌 | rollback 후 기존 결과 반환 |
| 목록 기본 조회 | 최신순 목록, `page=1`, `size=10` |
| 잘못된 페이지 값 | `422` |

### Worker

| 테스트 | 기대 결과 |
| --- | --- |
| 정상 JPEG/PNG | `(is_pneumonia, confidence_percent)` tuple 반환 |
| 출력 Confidence | `0.0~100.0` 및 유한값 |
| 입력 전처리 | `(1, 1, 128, 128)` 텐서와 `[0, 1]` 범위 |
| 손상 이미지 | `ValueError` |
| 존재하지 않는 파일 | `ValueError` |
| 모델 파일 누락·가중치 불일치 | `RuntimeError` |
| 같은 모델·같은 이미지 | 허용 오차 내 동일 출력 |
| 모델 초기화 반복 호출 | 가중치 재로딩 없이 동일 인스턴스 사용 |
| 클래스 매핑 | `index 0 = normal`, `index 1 = pneumonia` |

### 성능

- cold start와 warm inference를 구분해 측정한다.
- 캐시 miss와 hit를 각각 측정한다.
- 동시 사용자 수를 단계적으로 늘려 p50, p95, 최대 응답시간을 기록한다.
- 3초를 초과하면 모델 크기, 입력 크기, 실행 장치, Worker 분리를 재검토한다.

---

## 17. 구현 순서

1. 모델·API 담당자가 현재 Worker 공개 계약과 `MODEL_NAME`을 확인한다.
2. `AIAnalysisResult` nullable·고유 제약·인덱스 migration을 작성한다.
3. Prediction Schema와 Repository를 구현한다.
4. 캐시·권한·파일 검증을 포함한 Service를 구현한다.
5. `worker.model.predict_xray(Path)`를 Service에 연결한다.
6. API router를 생성하고 `app/main.py`에 등록한다.
7. 정상·실패·동시성 테스트를 작성한다.
8. Swagger UI에서 API 계약을 확인한다.
9. 독립 테스트 세트에서 모델 성능 기준을 검증한다.
10. 실제 실행 환경에서 3초 성능 기준을 측정한다.

---

## 18. 완료 조건

- [ ] 예측 실행 API가 진료기록의 저장 X-Ray를 사용한다.
- [ ] 같은 `record_id + ai_model` 결과가 있으면 추론 없이 반환한다.
- [ ] 결과 목록에 요구된 6개 필드가 포함된다.
- [ ] Heatmap 미생성 시 `null`을 정상 반환한다.
- [ ] 인증·권한·리소스 없음·Worker 실패 응답이 계약과 일치한다.
- [ ] 동시 요청에도 중복 결과가 DB에 저장되지 않는다.
- [ ] Recall 최소 `0.90`을 독립 테스트 세트에서 확인한다.
- [ ] Accuracy를 보조 지표로 기록한다.
- [ ] API p95 응답시간이 실제 대상 환경에서 3초 이내이다.
- [ ] Swagger UI와 자동화 테스트를 모두 통과한다.
- [ ] AI 보조 정보 안내가 화면에 표시된다.

---

## 19. 참고 자료

- 프로젝트 내부
  - `app/models/ai_analysis_result.py`
  - `app/models/medical_record.py`
  - `app/models/xray_image.py`
  - `worker/model.py`
  - `worker/models/README.md`
  - `docs/5일차_환자관리_API_설계.md`
- PyTorch, [torch.load](https://docs.pytorch.org/docs/stable/generated/torch.load.html)
- PyTorch, [Serialization semantics](https://docs.pytorch.org/docs/main/notes/serialization.html)
- PyTorch, [inference_mode](https://docs.pytorch.org/docs/stable/generated/torch.autograd.grad_mode.inference_mode.html)
- PyTorch, [Softmax](https://docs.pytorch.org/docs/stable/generated/torch.nn.modules.activation.Softmax.html)
- scikit-learn, [recall_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.recall_score.html)
- FDA, [Good Machine Learning Practice for Medical Device Development: Guiding Principles](https://www.fda.gov/medical-devices/software-medical-device-samd/good-machine-learning-practice-medical-device-development-guiding-principles)
- FDA, [Transparency for Machine Learning-Enabled Medical Devices: Guiding Principles](https://www.fda.gov/medical-devices/software-medical-device-samd/transparency-machine-learning-enabled-medical-devices-guiding-principles)
