"""Sync Redis client for the worker process.

ROLE: 양준혁 (D) — Worker 추론 담당
TARGET: worker/redis_client.py

Worker는 asyncio가 아니라 동기 루프로 돌아가므로 redis-py의 동기 클라이언트를 쓴다
(app 쪽 app/core/redis_client.py는 redis.asyncio를 쓰는 것과 다름 — 헷갈리지 말 것).

주의: 아래 큐/채널 이름과 메시지 포맷은 이희진이 PR #56(app/core/redis_client.py,
app/services/prediction_service.py)에서 이미 구현하고 merge 대기 중인 실제 계약이다.
임의로 바꾸면 워커와 app이 서로 통신하지 못하니 그대로 따를 것.
"""

from __future__ import annotations

import os

import redis

TASK_QUEUE_NAME = "prediction:jobs"
RESULT_CHANNEL_PREFIX = "prediction:results"  # 실제 채널명 = f"{RESULT_CHANNEL_PREFIX}:{job_id}"
BLPOP_TIMEOUT_SECONDS = 5  # 워커가 무한 대기하지 않고 주기적으로 깨어나게(로그 확인용)

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        # docker-compose.yml의 ai-worker 서비스에 REDIS_URL이 주입돼 있음 (PR #54 참고)
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        _client = redis.from_url(redis_url, decode_responses=True)
    return _client


def pop_next_task(timeout: int = BLPOP_TIMEOUT_SECONDS) -> dict | None:
    """큐에서 작업 하나를 원자적으로 꺼낸다. 없으면 timeout 후 None.

    BLPOP은 여러 워커가 동시에 호출해도 같은 작업을 두 워커가 동시에
    가져가지 않는다 (Redis가 원자적으로 보장) — 다중 워커 필수 요구사항은
    이 함수를 쓰기만 하면 자동으로 충족된다.

    큐에서 꺼낸 JSON을 파싱하면 아래 필드가 들어있다 (이희진이 실제 발행하는 형태):
        {"job_id": str, "record_id": int, "image_key": str, "model_name": str}

    - `image_key`는 "xray/uuid.png" 같은 **공유 볼륨 기준 상대경로**다.
      절대경로가 아니므로 사용할 때 MEDIA_ROOT와 직접 합쳐야 한다:
          MEDIA_ROOT = Path("/app/media")
          image_path = (MEDIA_ROOT / image_key).resolve()
          image_path.relative_to(MEDIA_ROOT)  # 경로 이탈 방지 검증
    """
    client = get_redis_client()
    # TODO: client.blpop(TASK_QUEUE_NAME, timeout=timeout)
    # 반환값은 (key, value) 튜플이거나 None. value는 JSON 문자열이므로 json.loads 필요.
    raise NotImplementedError


def publish_result(job_id: str, payload: dict) -> None:
    """추론 결과를 결과 채널(f"{RESULT_CHANNEL_PREFIX}:{job_id}")에 발행한다.

    이희진이 이미 구현한 포맷 (app/services/prediction_service.py의
    WorkerPredictionResponse Pydantic 모델과 정확히 일치해야 파싱됨):

        성공:
        {
          "job_id": "<job_id>",
          "status": "succeeded",
          "result": {
            "is_pneumonia": bool,
            "confidence": float,       # 0.0~100.0
            "heatmap_url": null,       # 현재 모델은 heatmap 미지원, 항상 null
            "model_name": "<받은 model_name 그대로>"
          },
          "error": null
        }

        실패:
        {
          "job_id": "<job_id>",
          "status": "failed",
          "result": null,
          "error": {"code": "invalid_xray_image" | "prediction_failed" | "model_unavailable"}
        }

    error.code는 반드시 아래 5개 중 하나여야 한다 (그 외 값은 app에서 검증 실패로 처리됨):
        invalid_image_path, xray_image_not_found, invalid_xray_image,
        model_unavailable, prediction_failed
    """
    client = get_redis_client()
    channel_name = f"{RESULT_CHANNEL_PREFIX}:{job_id}"
    # TODO: client.publish(channel_name, json.dumps(payload))
    raise NotImplementedError
