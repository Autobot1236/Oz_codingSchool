"""Async Redis client: enqueue prediction jobs, await worker results.

ROLE: 이희진 (A) — FastAPI ↔ Redis 연동 담당
TARGET: app/core/redis_client.py
GUIDE: ../../README.md 의 "메시지 흐름" 참고

이 파일은 스켈레톤입니다. TODO 부분만 채우면 됩니다.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

TASK_QUEUE_KEY = "prediction:tasks"
RESULT_CHANNEL_PREFIX = "prediction:result:"
RESULT_WAIT_TIMEOUT_SECONDS = 8  # NFR-PRED-002(3초 응답)을 고려해 값 조정

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """프로세스당 하나의 커넥션 풀을 재사용한다 (매 요청마다 새로 만들지 않음)."""
    global _redis_client
    if _redis_client is None:
        # TODO: settings에 REDIS_URL 필드를 추가하고 아래에서 사용
        # _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        raise NotImplementedError("settings.REDIS_URL 연결 코드 작성 필요")
    return _redis_client


async def enqueue_prediction_task(
    *,
    record_id: int,
    ai_model: str,
    image_path: str,
) -> str:
    """작업을 큐에 등록하고 이 요청을 식별할 request_id를 반환한다."""
    request_id = str(uuid.uuid4())
    payload = {
        "request_id": request_id,
        "record_id": record_id,
        "ai_model": ai_model,
        "image_path": image_path,
    }
    client = get_redis_client()
    # TODO: RPUSH TASK_QUEUE_KEY에 json.dumps(payload) 등록
    raise NotImplementedError


async def wait_for_prediction_result(request_id: str) -> tuple[bool, float]:
    """RESULT_CHANNEL_PREFIX + request_id 채널을 구독해서 워커 결과를 기다린다.

    양준혁(worker)과 합의된 결과 메시지 포맷 (worker/redis_client.py의
    publish_result와 반드시 동일해야 함):

        성공: {"status": "ok", "is_pneumonia": bool, "confidence": float}
        실패: {"status": "error", "error": "invalid_xray_image" | "prediction_failed"}

    - status == "ok" 이면 (is_pneumonia, confidence) 튜플로 반환
    - status == "error", error == "invalid_xray_image" 이면 ValueError를 던진다
      (prediction_service.py가 이미 ValueError를 422로 변환하는 분기가 있음)
    - status == "error", error == "prediction_failed" 등 그 외에는 RuntimeError를 던진다
    - RESULT_WAIT_TIMEOUT_SECONDS 안에 메시지가 없으면 TimeoutError를 던진다
      (prediction_service.py에서 503 model_unavailable로 변환)
    """
    channel_name = RESULT_CHANNEL_PREFIX + request_id
    client = get_redis_client()
    # TODO:
    # 1. client.pubsub()로 channel_name 구독
    # 2. RESULT_WAIT_TIMEOUT_SECONDS 안에 메시지가 오면 json.loads로 파싱
    # 3. 위 포맷대로 status 분기 처리
    # 4. 타임아웃이면 TimeoutError 발생시키기
    # 5. 반드시 finally에서 unsubscribe/close 처리 (커넥션 누수 방지)
    raise NotImplementedError
