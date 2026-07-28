# ROLE: 문홍주 (E) — Docker/인프라 담당
# TARGET: worker/Dockerfile
#
# app/Dockerfile과 같은 멀티스테이지 패턴을 재사용한다. 다른 점은:
#   - fastapi[standard], alembic 등 웹 전용 패키지는 필요 없음
#   - torch/numpy/pillow(AI 추론용)와 redis(큐 클라이언트)는 반드시 필요
#   - CMD가 uvicorn이 아니라 `python -m worker.main`
#
# pyproject.toml을 문홍주가 어떻게 나누느냐에 따라 아래 `uv sync` 줄이 달라짐.
# pyproject_split_notes.md에서 결정한 extra 이름을 그대로 여기에 반영할 것.

FROM ghcr.io/astral-sh/uv:0.8.11 AS uv

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
# TODO: pyproject_split_notes.md에서 정한 extra 이름으로 바꾸기
# 예: RUN uv sync --frozen --no-dev --no-install-project --extra ai
RUN uv sync --frozen --no-dev --no-install-project


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv ./.venv

# worker 실행에 실제로 필요한 것만 복사 (app/, alembic/, static/ 은 불필요)
COPY worker ./worker

RUN addgroup --system worker \
    && adduser --system --ingroup worker worker \
    && chown -R worker:worker /app

USER worker

# TODO: worker/main.py의 main()이 완성되면 그대로 CMD로 실행
CMD ["python", "-m", "worker.main"]
