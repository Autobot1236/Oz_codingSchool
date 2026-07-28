# AI Health — 폐렴 환자 관리 백오피스

회원·환자·진료기록·X-Ray·AI 예측 결과를 관리하는 폐렴 환자 관리 백오피스. FastAPI + MySQL + Redis + PyTorch(SimpleCNN) 기반으로, AI 추론은 별도의 워커 컨테이너로 분리되어 있다.

## 로컬 실행 방법

```bash
cp .env.example .env
# .env에 로컬 MySQL/Redis 접속 정보와 JWT_SECRET_KEY를 입력

docker compose up --build -d
docker compose exec fastapi alembic upgrade head
```

- FastAPI: http://localhost:8000 (Swagger: `/docs`)
- Adminer(DB 확인용): http://localhost:8080
- `ai-worker` 컨테이너는 별도 이미지로 빌드되며, `docker compose up -d --scale ai-worker=2`로 여러 개 동시 실행 가능

---

## 프로젝트 진행 회고

과제(웹 개발 트랙 프로젝트, 2026-07-13 ~ 2026-07-29)를 진행하며 각 단계를 어떤 방식으로 진행했는지 정리한다.

### 1. Team Rule 정의

`docs/1일차_team_rules.md`에 코어타임(수업 후 최소 30분 진행상황 공유), 1일 1커밋, 커밋 컨벤션(`feat`/`fix`/`docs`/`style`/`refactor`/`chore`), PR 최소 1인 리뷰 후 병합, 공용 파일(`app/main.py`, `app/core/`, `docker-compose.yml`, `pyproject.toml` 등) 수정 전 팀 채널 공유 규칙을 정의했다.

**실제로 지켜본 결과**: 규칙은 명확했지만 100% 예방되진 않았다. Stage 3에서 문홍주(Docker 인프라, PR #54)와 이희진(Redis 연동, PR #56)이 동시에 `docker-compose.yml`·`pyproject.toml`을 수정하면서 실제로 merge 충돌이 발생했다. "공용 파일은 사전 공유"라는 규칙이 있어도, PR을 짧은 시간 안에 병렬로 진행하면 충돌 자체는 피하기 어렵다는 걸 확인했고, 대신 "충돌이 나면 당황하지 않고 rebase로 정리한다"는 대응 절차가 실질적으로 더 중요했다.

### 2. 사용자 요구사항 정의

도메인별로 `REQ-*`(기능), `NFR-*`(비기능) ID를 붙인 요구사항 정의서를 작성했다 (`4일차_USER_요구사항_정의서.md` 등). 액터(비로그인/PENDING/STAFF/ADMIN)와 상태 전이를 표로 정리하고, 범위 포함/제외를 명시적으로 나눴다.

**실제로 겪은 일**: AI 예측 기능(Stage 6)의 초기 요구사항 정의서는 이후 Stage 3에서 실제로 구현한 것과 응답 포맷·엔드포인트 경로가 달라져 있었다 (`/ai-predictions` vs 초안의 다른 경로 등). 요구사항 문서는 구현 전 합의를 위한 것이지 고정된 명세가 아니며, 실제 구현이 확정되면 문서를 다시 맞추는 과정이 한 번 더 필요했다.

### 3. API 명세서 작성

Stage마다 `docs/N일차_*_API_설계.md`를 작성해 HTTP Method·경로·요청/응답 스키마·오류 코드를 팀 합의 전에 문서화했다. 예측 API 설계 문서(`6일차_폐렴예측_API_설계.md`)에는 성공/실패 응답 포맷과 에러 코드 표를 미리 정의해뒀다.

**실제로 겪은 일**: 이 문서 초안은 Celery + `task_id` 폴링 방식을 전제로 했지만(4번 항목 참고), Stage 3에서 실제로는 Redis List/Pub-Sub 기반의 동기식 단일 요청-응답으로 구현했다. 명세서를 먼저 쓰고 그대로 구현하기보다, "구현하면서 더 간단한 방법이 보이면 명세서를 갱신한다"는 순서가 이 프로젝트에는 더 맞았다.

### 4. Git & GitHub Branch 전략 구성

`docs/2일차_git_branch_전략.md`에서 Git Flow와 GitHub Flow를 비교하고, 단기 프로젝트라는 이유로 **GitHub Flow**(main + 작업 브랜치, release 브랜치 없음)를 선택했다. 브랜치 이름은 `feature/기능명`, `docs/문서명`, `fix/오류명` 규칙을 정했다.

**실제로 겪은 일**: 원래 계획은 main 하나만 쓰는 것이었지만, 실제로는 `develop` 브랜치도 함께 운영하며 기능 브랜치 → develop → main 순서로 병합했다 (계획 대비 변형). Stage 3부터는 AI Agent가 작업한 브랜치를 구분하기 위해 `agent/*` 네이밍도 추가로 썼다 (예: `agent/moon-stage3-worker-infra`, `fix/worker-redis-socket-timeout`). 팀원 5명이 만든 브랜치(`feature/HJ-*`, `feature/SI-*`, `feature/practice-api_stage10_*` 등)와 AI Agent가 만든 브랜치가 같은 저장소에서 같은 PR 리뷰·병합 절차를 따랐다.

### 5. 프로젝트 세팅

`uv`로 파이썬 의존성을 관리하고, FastAPI(비동기) + SQLAlchemy(AsyncSession) + Alembic + MySQL 조합으로 초기 세팅했다. 민감정보는 `.env`로 분리하고 `.env.example`을 공유했다.

**실제로 겪은 일**: Stage 3에서 AI 추론(torch/numpy/pillow)을 워커 전용 의존성으로 분리하면서, `pyproject.toml`을 `[project.optional-dependencies] ai = [...]`로 재구성했다. `uv sync --extra ai`가 `ai` extra만이 아니라 base dependencies(`asyncmy` 포함)도 항상 함께 설치한다는 걸 실제로 빌드해보고서야 알았고, `asyncmy`가 컴파일이 필요해서 워커 이미지에도 `build-essential`을 넣어야 했다.

### 6. API 및 AI 워커 코드 작성 후 Branch 전략을 통한 코드 병합

역할을 A(총괄/PR 통합) ~ E(프론트/Docker)로 나눠 Stage 2·4·5에서는 전원이 최소 1개 API를 직접 구현했고, Stage 3(Redis+AI 워커 분리)에서는 담당을 세분화했다.

| 담당 | Stage 3 역할 | PR |
| --- | --- | --- |
| 이희진 (A) | FastAPI ↔ Redis 연동, 큐 등록/구독 | #56 |
| 양준혁 (D) | Worker 큐 소비/추론/결과 발행 | #58 |
| 안상균 (C) | 동시성 검증 테스트(mock + 실제 동시요청 스크립트) | #59 |
| 문홍주 (E) | Docker 인프라, 의존성 분리, Redis 컨테이너 | #54 |
| 이수인 (B) | 예측 API 권한 체크(STAFF/ADMIN) 검증 | (기존 구현 확인) |

각자 담당 파일을 스켈레톤/가이드(`docs/stage3_role_guide/`)로 먼저 계약(큐 이름, 메시지 포맷, 에러 코드)을 맞춘 뒤 병렬로 구현하고, PR 리뷰 후 순서대로 병합했다 (#56 → #58 → #54 → #59, 버그 수정 #60).

### 7. 아키텍처 설계 및 적용

`docs/9일차_동시성문제_해결을위한_아키텍처설계.md`에서 Redis Pub/Sub·Redis Streams·Celery+Redis 세 가지 방식을 비교했고, 초안에서는 **Celery + Redis**를 1차 구현으로 채택했다.

**실제로는 다르게 갔다**: 실제 Stage 3 구현 단계에서 Celery 대신 **순수 Redis(List `RPUSH`/`BLPOP` 큐 + Pub/Sub 결과 전달)**로 방향을 바꿨다. 이유는 (1) 과제 요구사항 자체가 `202 Accepted` + 폴링이 아니라 한 번의 HTTP 요청-응답으로 끝나는 동기적 흐름을 전제로 했고, (2) 팀 전원이 Celery를 처음 다루는데 마감이 임박했고, (3) 다중 워커 지원(필수 요구사항)은 `BLPOP`의 원자성만으로 이미 충족됐고, (4) Celery가 강점을 갖는 재시도·가시성 타임아웃 등은 과제에서 "선택" 항목과 겹쳤기 때문이다. 문서와 구현이 벌어진 걸 확인한 뒤 문서를 실제 구현에 맞게 다시 수정했다 (4.4절 결정 배경 추가).

### 8. 도커 인프라 관련 파일 작성

`app/Dockerfile`(FastAPI)과 `worker/Dockerfile`(AI 추론)을 멀티스테이지 빌드로 분리했다. `docker-compose.yml`에 `fastapi`/`mysql`/`redis`/`ai-worker` 서비스를 정의하고, `ai-worker`는 `./media:/app/media`만 공유 마운트해 앱 소스코드나 `.env`는 노출하지 않도록 했다.

**실제로 겪은 문제와 수정**:
- `docker-compose.yml`의 `command` 리스트 들여쓰기 오류로 `uvicorn`이 `--port` 인자를 못 받아 fastapi 컨테이너가 죽는 문제 — 발견 후 즉시 수정
- Redis 클라이언트의 `socket_timeout`이 `BLPOP` 타임아웃과 정확히 같아서, 큐가 비어 있을 때마다 정상 상황을 `TimeoutError`로 오인하는 문제 — 실제로 4개 컨테이너를 함께 띄워 워커 로그를 보다가 발견해서 수정 (PR #60)

두 버그 모두 각 서비스를 개별적으로(mock, 유닛테스트) 검증할 때는 드러나지 않고, **전체 스택을 실제로 함께 띄워봤을 때만** 발견됐다.

### 9. AWS 배포

선택 과제(Stage 5)로 분류되어 있었고, 일정상(마감 2026-07-29) 필수 Stage 1~4를 완료하는 데 우선순위를 두어 진행하지 않았다.

### 10. QA 진행

- **유닛 테스트**: Redis 클라이언트, 예측 서비스(캐시/에러 매핑), 동시성 시나리오를 mock 기반 유닛테스트로 검증
- **실제 동시성 테스트**: 같은 진료기록에 대한 예측 요청 2개를 `threading.Barrier`로 완전히 동시에 전송해, DB에 중복 없이 하나의 결과로 수렴하는지 실제 서버에 대고 검증 (`scripts/test_prediction_concurrency.py`)
- **엔드투엔드 검증**: `mysql`+`redis`+`fastapi`+`ai-worker` 4개 컨테이너를 모두 띄운 뒤 회원가입 → 로그인 → 환자 등록 → 진료기록(X-Ray) 등록 → 예측 요청까지 실제 HTTP 요청으로 전체 흐름을 확인했다. 최초 요청은 캐시 미스로 Redis 큐 등록 → 워커 추론 → Pub/Sub 결과 전달 → DB 저장까지 거쳐 약 0.1초 내 응답했고, 재요청은 DB 캐시로 즉시 응답했다.
- **권한 검증**: `PENDING` 역할 사용자는 예측 API에서 `403 prediction_access_denied`로 차단되고, `STAFF`로 승격한 사용자만 정상 호출되는 것을 확인했다.

---

## Alembic Migration Guide

이 프로젝트는 데이터베이스 마이그레이션을 위해 Alembic을 사용합니다.

### 1. 마이그레이션 파일 생성 (자동 생성)
모델(`app/models/`)이 변경된 경우 다음 명령어를 실행하여 마이그레이션 파일을 생성합니다.
```bash
uv run alembic revision --autogenerate -m "변경 내용 설명"
```

### 2. 데이터베이스에 반영
생성된 마이그레이션을 데이터베이스에 적용하려면 다음 명령어를 실행합니다.
```bash
uv run alembic upgrade head
```

### 3. 이전 상태로 되돌리기 (Rollback)
마지막 마이그레이션을 취소하려면 다음 명령어를 실행합니다.
```bash
uv run alembic downgrade -1
```
