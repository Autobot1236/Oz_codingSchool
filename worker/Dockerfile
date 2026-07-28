FROM ghcr.io/astral-sh/uv:0.8.11 AS uv

FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

# `uv sync --extra ai`는 ai extra만이 아니라 base dependencies(asyncmy 포함)도
# 함께 설치한다. asyncmy는 소스 컴파일이 필요해서 build-essential이 있어야 한다.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra ai


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv ./.venv

# worker 실행에 실제로 필요한 것만 복사 (app/, alembic/, static/ 은 불필요)
COPY worker ./worker

RUN mkdir -p /app/media \
    && addgroup --system worker \
    && adduser --system --ingroup worker worker \
    && chown -R worker:worker /app

USER worker

CMD ["python", "-m", "worker.main"]
