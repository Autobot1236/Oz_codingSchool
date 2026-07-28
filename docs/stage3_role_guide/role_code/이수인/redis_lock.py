"""(선택 기능) Redis 기반 분산 락 — 같은 record_id+ai_model 중복 처리 방지.

ROLE: 이수인 (B) — 선택 기능
TARGET: app/core/redis_lock.py (신규 파일)

우선순위 낮음. Stage 3 필수 요구사항(다중 워커 지원)은 이미 BLPOP의 원자성으로
충족되므로, 이 파일은 "캐시 조회 직후 ~ 큐 등록 사이"의 짧은 경쟁 상태까지
막고 싶을 때만 추가하면 된다.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from app.core.redis_client import get_redis_client

LOCK_TTL_SECONDS = 10  # 락을 잡은 요청이 죽어도 이 시간 후엔 자동 해제


def _lock_key(record_id: int, ai_model: str) -> str:
    return f"prediction:lock:{record_id}:{ai_model}"


@asynccontextmanager
async def prediction_lock(record_id: int, ai_model: str):
    """with 블록 동안 이 record_id+ai_model에 대한 락을 잡는다.

    락을 못 잡으면 (이미 다른 요청이 처리 중이면) TimeoutError를 던져서
    prediction_service.py가 503으로 응답하게 한다 — 즉시 재시도하지 말고
    호출자가 GET /predictions로 폴링하게 유도.
    """
    client = get_redis_client()
    key = _lock_key(record_id, ai_model)
    # TODO: client.set(key, "1", nx=True, ex=LOCK_TTL_SECONDS)로 락 획득 시도
    # 실패하면 TimeoutError, 성공하면 try/finally로 client.delete(key)까지 구현
    raise NotImplementedError
