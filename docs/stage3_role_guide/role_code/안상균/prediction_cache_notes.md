# 캐시·동시성 리뷰 가이드 (안상균 담당)

새 파일을 만드는 작업이 아니라, 이희진이 고친 `app/services/prediction_service.py`를
**리뷰하고 동시성 관점에서 구멍이 없는지 확인**하는 역할입니다. Stage 6에서 이미
만든 캐시/저장 로직을 다시 쓰는 게 아니라 "여전히 유효한지" 확인하는 게 핵심입니다.

## 이미 있는 것 (건드릴 필요 없음)

- `get_cached_prediction()` — `record_id + ai_model`로 기존 결과 조회. Redis 큐잉을 붙여도
  이 함수는 **큐에 작업을 넣기 전에 그대로 먼저 호출**되어야 한다. 이희진의 패치에서
  이 호출 순서가 유지되는지 확인할 것.
- `save_prediction_result()` — `IntegrityError` 발생 시 rollback 후 기존 결과를 재조회해서
  반환하는 로직이 이미 있음 (`app/models/ai_analysis_result.py`의 unique 제약을 사용).

## Stage 3에서 새로 생기는 동시성 케이스

Redis 큐잉이 들어오면서 **캐시 조회와 큐 등록 사이의 시간 간격이 생긴다.** 이 사이에
같은 `record_id + ai_model`로 두 번째 요청이 들어오면:

1. 요청 A: 캐시 miss → 큐에 작업 등록
2. 요청 B (거의 동시): 캐시 miss (A의 결과가 아직 저장 전) → 큐에 작업 등록
3. 워커가 두 작업을 각각 처리 → 추론 2번 실행됨 (낭비지만 위험하진 않음)
4. A 저장 성공, B는 `save_prediction_result()`의 `IntegrityError` 분기를 타고
   A의 결과를 재조회해서 반환 → **최종 DB 상태는 안전함**

## 확인할 것

- [ ] 위 4번 분기(`IntegrityError` → rollback → 재조회)가 Redis 큐잉 경로에서도
      그대로 호출되는지 (이희진의 패치가 `save_prediction_result()` 호출부는
      안 건드렸는지 diff로 확인)
- [ ] 워커가 중복 추론을 한다는 것 자체가 문제인지 팀과 상의 — 문제라면 이수인의
      `redis_lock.py`(선택 기능)로 "이 record_id+ai_model은 이미 처리 중"이라는
      락을 캐시 조회와 큐 등록 사이에 걸도록 제안
- [ ] `AIAnalysisResult`의 unique 제약(`record_id`, `ai_model`)이 Stage 6 마이그레이션에
      실제로 적용돼 있는지 `alembic` 히스토리에서 재확인 (DB 레벨 안전장치가 없으면
      위 시나리오에서 중복 행이 그냥 쌓임)
