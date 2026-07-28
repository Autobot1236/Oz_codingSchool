# prediction_service.py 패치 가이드 (이희진 담당)

대상 파일: `app/services/prediction_service.py`
함수: `predict_pneumonia()`

## 지금 이 블록을 (현재: 프로세스 내부에서 직접 추론)

```python
try:
    await run_in_threadpool(load_model)
except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=MODEL_UNAVAILABLE_DETAIL,
    ) from exc

try:
    is_pneumonia, confidence = await run_in_threadpool(
        predict_xray,
        image_path,
    )
except ValueError as exc:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=INVALID_XRAY_IMAGE_DETAIL,
    ) from exc
except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=PREDICTION_FAILED_DETAIL,
    ) from exc
```

## 이렇게 바꾼다 (Redis 큐잉으로 대체)

```python
from app.core.redis_client import enqueue_prediction_task, wait_for_prediction_result

# ...

try:
    request_id = await enqueue_prediction_task(
        record_id=record_id,
        ai_model=MODEL_NAME,
        image_path=str(image_path),
    )
    is_pneumonia, confidence = await wait_for_prediction_result(request_id)
except TimeoutError as exc:
    # 워커가 죽었거나 큐가 밀린 경우. NFR-PRED-002(3초) 기준으로 타임아웃 값을 정한다.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=MODEL_UNAVAILABLE_DETAIL,
    ) from exc
except ValueError as exc:
    # 워커가 이미지 디코딩 실패를 알려온 경우
    # (redis_client.py의 wait_for_prediction_result가 status:"error",
    #  error:"invalid_xray_image"를 받으면 ValueError로 변환해서 던져줌)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=INVALID_XRAY_IMAGE_DETAIL,
    ) from exc
except Exception as exc:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=PREDICTION_FAILED_DETAIL,
    ) from exc
```

## 이미 확정된 것 (더 이상 논의 불필요)

- **`image_path` 포맷**: `resolve_xray_image_path()`가 이미 컨테이너 안의 **절대 경로**
  (`/app/media/xray/...`)를 돌려주고 있음. fastapi와 ai-worker 컨테이너가 둘 다
  `.:/app`로 레포 전체를 마운트하므로 `str(image_path)` 그대로 넘기면 워커 쪽에서도
  같은 경로가 그대로 유효함 — 별도 변환 로직 필요 없음.
- **결과 메시지 포맷**: 성공 `{"status": "ok", "is_pneumonia", "confidence"}`,
  실패 `{"status": "error", "error": "invalid_xray_image"|"prediction_failed"}`로
  양준혁 쪽과 이미 합의·반영해둠 (`redis_client.py` 최신 버전 참고).

## 체크리스트

- [ ] `worker.model`의 `load_model`, `predict_xray` import를 prediction_service.py에서
      제거해도 되는지 확인 (더 이상 이 프로세스에서 직접 호출하지 않으므로 제거 가능,
      단 `MODEL_NAME`은 큐 메시지에 필요하므로 계속 import)
- [ ] `get_cached_prediction()` 캐시 조회는 그대로 유지 (안상균 담당 영역, 건드리지 않음)
- [ ] `save_prediction_result()` 호출부도 그대로 유지 — 워커에서 받은 `(is_pneumonia, confidence)`를
      기존과 동일하게 넘기기만 하면 됨
