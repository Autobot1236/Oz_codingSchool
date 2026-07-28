# 인증/권한 검증 체크리스트 (이수인 담당)

새 코드를 쓰는 작업이 아니라 **Redis 큐잉으로 바뀐 뒤에도 인증이 그대로 걸리는지 검증**하는 역할입니다.

## 현재 상태 (실제 코드 확인 결과)

`app/apis/medical_records.py`의 예측 엔드포인트 두 개(`predict_pneumonia`, `list_predictions`)는
현재 `Depends(get_current_user)`만 걸려 있습니다 — 즉 **로그인만 하면 누구나 호출 가능**하고,
원래 설계 문서(REQ-PRED-001)에서 요구했던 `STAFF`/`ADMIN` 역할 제한이나 부서(`MEDICAL`/`DEV`/`RESEARCH`)
제한은 아직 코드에 없습니다.

## 확인/작업할 것

- [ ] 이게 Stage 3 범위인지 팀과 확인 — 원래 설계 문서 기준으로는 권한 제한이 있어야 하므로,
      시간이 되면 `app/core/security.py`에 `require_staff_or_admin` 같은 dependency를 추가해서
      두 엔드포인트에 `Depends(get_current_user)` 대신 적용하는 것을 제안
- [ ] Redis 큐잉이 들어와도 인증 체크는 **라우터 단계(요청이 큐에 들어가기 전)**에서 그대로
      실행되므로 추가로 바꿀 게 없다는 것만 확인 — 워커는 인증 정보를 아예 모르는 채로
      동작하므로(요청 바디에 user 정보를 넣지 않음) 워커 쪽에 권한 로직을 넣을 필요는 없음
- [ ] Swagger에서 로그인 없이 `POST .../predict` 호출 시 401이 나오는지, 다른 사용자의
      진료기록 record_id로도 호출이 되는지(현재는 환자 소유권 체크가 없어 보임 — 팀 논의 필요)

## (선택) 동시 요청 중복 방지

시간이 남으면 `안상균_prediction_cache_notes.md`에서 언급한 "캐시 조회~큐 등록 사이의 경쟁 상태"를
막는 분산 락을 추가할 수 있습니다. `role_code/이수인/redis_lock.py` 스켈레톤 참고.

## (선택) 워커 비정상 종료 시 복구

워커가 작업을 BLPOP으로 꺼낸 직후 죽으면 그 작업은 유실됩니다. 우선순위는 낮지만 시간이
남으면 `worker/main.py`(양준혁 담당)의 BLPOP을 BRPOPLPUSH 기반 "processing 리스트" 패턴으로
바꾸는 걸 같이 검토해볼 수 있습니다.
