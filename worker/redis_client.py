"""Synchronous Redis client used by the AI worker."""

from __future__ import annotations

import json
import os
from typing import Any

import redis

TASK_QUEUE_KEY = "prediction:jobs"
RESULT_CHANNEL_PREFIX = "prediction:results:"
BLPOP_TIMEOUT_SECONDS = 5

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Return the process-wide Redis connection.

    socket_timeout must exceed BLPOP_TIMEOUT_SECONDS. BLPOP asks the *server*
    to hold the connection open for up to `timeout` seconds before replying
    with a nil; if the client-side socket timeout is equal to (or shorter
    than) that value, the client's own read can time out at essentially the
    same instant the server would have replied, raising
    redis.exceptions.TimeoutError on almost every idle poll instead of the
    library's normal "no item" (None) result.
    """
    global _client
    if _client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=BLPOP_TIMEOUT_SECONDS + 5,
        )
    return _client


def pop_next_task(timeout: int = BLPOP_TIMEOUT_SECONDS) -> dict[str, Any] | None:
    """Remove and decode the oldest prediction job.

    FastAPI enqueues jobs with RPUSH and the worker consumes them with BLPOP,
    so jobs are handled in first-in, first-out order.
    """
    item = get_redis_client().blpop(TASK_QUEUE_KEY, timeout=timeout)
    if item is None:
        return None

    _, raw_payload = item
    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("Prediction job payload must be a JSON object.")
    return payload


def publish_result(job_id: str, payload: dict[str, Any]) -> None:
    """Publish one UTF-8 JSON result to the job-specific channel."""
    channel = f"{RESULT_CHANNEL_PREFIX}{job_id}"
    message = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    get_redis_client().publish(channel, message)
