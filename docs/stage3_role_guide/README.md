# Stage 3 — Redis + AI 워커 분리 역할 가이드

이 폴더는 **구현 코드가 아니라 스켈레톤/가이드**입니다. 각자 담당 파일의 TODO를 채운 뒤
`role_code/<이름>/` 안의 파일을 안내된 `TARGET` 경로로 옮기거나 내용을 병합하세요.

## 진행 상황 (2026-07-28 업데이트)

- ✅ **문홍주**: Redis 컨테이너, `pyproject.toml` 분리, `worker/Dockerfile`, `ai-worker` compose 서비스 — PR #54 (merge 대기)
- ✅ **이희진**: `app/core/redis_client.py`, `prediction_service.py` 패치 — **이미 실제 코드로 구현 완료, PR #56에서 merge 대기 중.** 아래 "메시지 흐름"은 PR #56의 실제 구현 기준으로 갱신했습니다. 이희진 폴더의 스켈레톤은 더 이상 참고할 필요 없이 PR #56을 직접 보세요.
- 🔲 **양준혁**: `worker/redis_client.py`, `worker/main.py` — 아직 미착수. 스켈레톤을 PR #56의 실제 계약에 맞춰 갱신해뒀으니 이걸 기준으로 작업하세요.
- 🔲 **안상균**, **이수인**: 아직 미착수

**PR #54와 PR #56은 `docker-compose.yml`, `pyproject.toml`을 동시에 건드려서 merge 순서에 따라 충돌이 날 수 있습니다.** 둘 중 하나를 먼저 merge하고 나머지 브랜치를 rebase하는 걸 권장합니다.

## 먼저 확인할 것

- `docker-compose.yml`의 `fastapi.command` 블록 들여쓰기 문제는 별도 PR(#55 문서 수정과 함께 확인)로 이미 고쳐졌습니다.
- Stage 3의 핵심은 `prediction_service.py`의 `predict_pneumonia()`가 FastAPI 프로세스 안에서 직접 모델을 로드하던 것을 Redis 큐잉으로 바꾸는 것이었고, **이희진이 PR #56에서 이미 구현했습니다.**
- 캐시 체크(`get_cached_prediction`)와 DB 저장(`save_prediction_result`, unique 제약 기반 동시 저장 방지)은 Stage 6에서 이미 구현돼 있고, PR #56도 이 부분을 그대로 유지합니다.

## 메시지 흐름 (PR #56 실제 구현 기준)

```
FastAPI                          Redis                         Worker
  │  SUBSCRIBE prediction:results:{job_id}  (먼저 구독!)           │
  │  RPUSH prediction:jobs  →   [list]                            │
  │                              [list]  ← BLPOP  ──────────────  │  (여러 워커가 떠 있어도
  │                                                                   BLPOP은 원자적이라 한
  │                                                                   워커만 작업을 가져감)
  │                                                               │  predict_xray() 실행
  │  ← PUBLISH prediction:results:{job_id}  ─────────────────────  │
```

- 큐 이름: `prediction:jobs` (Redis List, `RPUSH`/`BLPOP`)
- 결과 채널: `prediction:results:{job_id}` (요청마다 고유한 `job_id` = `uuid4()`)
- **먼저 구독 → 그 다음 큐 등록** 순서가 중요합니다. Pub/Sub은 메시지를 보관하지 않기 때문에, 큐 등록이 먼저 일어나면 워커가 아주 빠르게 응답할 경우 결과를 놓칠 수 있습니다. 이희진의 구현은 구독이 실제로 걸렸는지(`type: subscribe` 메시지 수신)까지 확인한 뒤에 큐에 등록합니다.
- FastAPI의 결과 대기 타임아웃은 `PREDICTION_TIMEOUT_SECONDS`(기본 2.5초, `app/core/config.py`)입니다. **워커가 요청마다 모델을 새로 로딩하면 이 시간을 넘깁니다 — 워커 시작 시 모델을 미리 로딩해두는 게 필수입니다.**

**작업 메시지** (FastAPI → Worker, `RPUSH`):
```json
{"job_id": "uuid", "record_id": 10, "image_key": "xray/uuid.png", "model_name": "simple-cnn-state-dict-v1"}
```
`image_key`는 **공유 볼륨(`/app/media`) 기준 상대경로**입니다 (`"xray/uuid.png"`). 워커는
`Path("/app/media") / image_key`로 절대경로를 직접 만들어야 합니다.

**결과 메시지** (Worker → FastAPI, `PUBLISH`):
```json
// 성공
{"job_id": "uuid", "status": "succeeded", "result": {"is_pneumonia": true, "confidence": 94.28, "heatmap_url": null, "model_name": "simple-cnn-state-dict-v1"}, "error": null}
// 실패
{"job_id": "uuid", "status": "failed", "result": null, "error": {"code": "invalid_xray_image"}}
```
`error.code`는 반드시 다음 5개 중 하나: `invalid_image_path`, `xray_image_not_found`, `invalid_xray_image`, `model_unavailable`, `prediction_failed`. 이희진 쪽이 Pydantic으로 이 포맷을 엄격하게 검증하므로 **임의로 필드를 빼거나 다른 이름을 쓰면 파싱 에러가 납니다.**

## 공통 준비물

- `pyproject.toml`에 `redis` 패키지 — PR #56에서 이미 추가됨
- `REDIS_URL`, `PREDICTION_QUEUE_NAME`, `PREDICTION_RESULT_CHANNEL_PREFIX`, `PREDICTION_TIMEOUT_SECONDS` — PR #56에서 `app/core/config.py`·`.env.example`에 이미 추가됨. 워커도 `REDIS_URL` 환경변수를 그대로 사용하면 됨 (docker-compose의 `ai-worker` 서비스에 이미 주입돼 있음, PR #54).

## 담당자별 파일

| 담당자 | 상태 | 파일 |
| --- | --- | --- |
| 이희진 (A) | ✅ 완료 (PR #56) | `app/core/redis_client.py`, `app/services/prediction_service.py` |
| 양준혁 (D) | 🔲 미착수 | `role_code/양준혁/redis_client.py` → `worker/redis_client.py` |
| 양준혁 (D) | 🔲 미착수 | `role_code/양준혁/main.py` → `worker/main.py` |
| 안상균 (C) | 🔲 미착수 | `role_code/안상균/prediction_cache_notes.md` (PR #56 리뷰 가이드) |
| 이수인 (B) | 🔲 미착수 | `role_code/이수인/permission_check_notes.md` |
| 이수인 (B, 선택) | 🔲 미착수 | `role_code/이수인/redis_lock.py` (선택 기능) |
| 문홍주 (E) | ✅ 완료 (PR #54) | `worker/Dockerfile`, `docker-compose.yml`의 `ai-worker` 서비스, `pyproject.toml` 분리 |

## 통합 순서 (남은 것)

1. **PR #54, #56 merge 순서 정하고 충돌 해결** (둘 다 `docker-compose.yml`/`pyproject.toml` 겹침)
2. 양준혁 — `worker/redis_client.py`, `worker/main.py` 구현 (갱신된 스켈레톤 기준). `python -m worker.main`으로 로컬 단독 테스트 가능 (redis 컨테이너만 있으면 됨)
3. 안상균 — PR #56 코드 리뷰 (캐시/동시성 관점)
4. 이수인 — 권한 체크 확인 + (선택) 동시 요청 중복 방지
5. 전원 — Swagger에서 `POST .../predict` 호출 → 워커 로그에 작업 처리 기록 → 결과 응답 확인
