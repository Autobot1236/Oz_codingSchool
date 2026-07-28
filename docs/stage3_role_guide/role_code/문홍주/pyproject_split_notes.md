# pyproject.toml 의존성 분리 가이드 (문홍주 담당)

## 현재 상태 (실제 pyproject.toml)

```toml
dependencies = [
    "alembic>=1.18.4",
    "argon2-cffi>=25.1.0",
    "asyncmy>=0.2.11",
    "cryptography>=46.0.6",
    "fastapi[standard]>=0.135.3",
    "numpy>=2.0.0",
    "pillow>=11.0.0",
    "pydantic-settings>=2.13.1",
    "python-jose[cryptography]>=3.5.0",
    "sqlalchemy[asyncio]>=2.0.49",
    "torch>=2.7.0",
    "uuid6>=2025.0.1",
]
```

`torch`(CPU 버전이어도 수백MB), `numpy`, `pillow`가 fastapi 이미지에도 그대로 들어가서
이미지가 불필요하게 커집니다. Stage 1 완료조건과는 무관하지만 Stage 3 목표(이미지 용량 최소화)와 관련.

## 할 일

1. `redis` 패키지를 core dependencies에 추가 (app, worker 둘 다 필요)
2. `torch`, `numpy`, `pillow`를 optional-dependencies로 분리

```toml
[project]
dependencies = [
    "alembic>=1.18.4",
    "argon2-cffi>=25.1.0",
    "asyncmy>=0.2.11",
    "cryptography>=46.0.6",
    "fastapi[standard]>=0.135.3",
    "pydantic-settings>=2.13.1",
    "python-jose[cryptography]>=3.5.0",
    "redis>=5.0.0",
    "sqlalchemy[asyncio]>=2.0.49",
    "uuid6>=2025.0.1",
]

[project.optional-dependencies]
ai = [
    "numpy>=2.0.0",
    "pillow>=11.0.0",
    "torch>=2.7.0",
]

[tool.uv.sources]
torch = [{ index = "pytorch-cpu", marker = "sys_platform == 'linux'" }]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true
```

3. 빌드 커맨드 조정
   - `app/Dockerfile` (기존, 그대로): `uv sync --frozen --no-dev --no-install-project`
     → torch가 빠지므로 자동으로 이미지가 작아짐. **단, `worker/model.py`를 import하는
     코드가 app 쪽에 남아있으면 ImportError가 나므로, prediction_service.py가 더 이상
     `worker.model`을 직접 import하지 않는지 이희진의 패치 이후 확인할 것.**
   - `worker/Dockerfile` (신규): `uv sync --frozen --no-dev --no-install-project --extra ai`

## 확인할 것

- [ ] `uv sync --extra ai` 문법이 현재 uv 버전(0.8.11)에서 동작하는지 로컬에서 먼저 테스트
      (버전에 따라 `--group`/`--extra` 문법이 다를 수 있음)
- [ ] app 이미지 재빌드 후 `docker images`로 용량이 실제로 줄었는지 확인
- [ ] worker 이미지 빌드 시 torch 다운로드가 오래 걸리므로(약 150MB) 첫 빌드는
      시간 여유를 두고 진행 — 이후엔 uv/docker 캐시로 빨라짐
