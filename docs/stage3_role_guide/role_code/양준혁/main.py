"""Worker entrypoint: consume prediction tasks, run inference, publish results.

ROLE: 양준혁 (D) — Worker 추론 담당
TARGET: worker/main.py

실행: `docker compose exec ai-worker python -m worker.main` (문홍주의 compose 서비스와 맞출 것)
또는 로컬 테스트: `uv run python -m worker.main` (redis 컨테이너만 떠 있으면 됨)

주의: 큐/채널 이름과 메시지 포맷은 이희진이 PR #56에서 이미 구현한 실제 계약이다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from worker.model import MODEL_NAME, load_model, predict_xray
from worker.redis_client import pop_next_task, publish_result

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-worker")

MEDIA_ROOT = Path("/app/media")


def _resolve_image_path(image_key: str) -> Path:
    """image_key("xray/uuid.png")를 실제 파일 경로로 변환하고 검증한다.

    주의: worker/model.py의 predict_xray()는 파일이 없을 때도 내부적으로
    OSError를 잡아 ValueError로 변환해버리므로, "파일 없음"과 "이미지 손상"을
    구분하려면 predict_xray를 부르기 전에 여기서 존재 여부를 먼저 확인해야 한다.
    """
    candidate = (MEDIA_ROOT / image_key).resolve()
    candidate.relative_to(MEDIA_ROOT)  # MEDIA_ROOT 밖이면 ValueError
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def handle_task(task: dict) -> None:
    """작업 하나를 처리한다. 예외를 여기서 잡아서 결과 채널로 에러를 알려준다.

    task 형태 (이희진의 request_worker_prediction()이 실제로 RPUSH하는 것과 동일):
        {"job_id": str, "record_id": int, "image_key": str, "model_name": str}
    """
    job_id = task["job_id"]
    image_key = task["image_key"]

    logger.info("작업 시작: record_id=%s job_id=%s", task.get("record_id"), job_id)

    try:
        image_path = _resolve_image_path(image_key)
    except FileNotFoundError:
        # _resolve_image_path가 존재 여부까지 미리 확인함 (predict_xray는 이 구분을 못 함)
        publish_result(job_id, {
            "job_id": job_id,
            "status": "failed",
            "result": None,
            "error": {"code": "xray_image_not_found"},
        })
        logger.warning("이미지 파일 없음: job_id=%s image_key=%s", job_id, image_key)
        return
    except ValueError:
        # MEDIA_ROOT 밖으로 벗어나는 image_key (경로 이탈 시도)
        publish_result(job_id, {
            "job_id": job_id,
            "status": "failed",
            "result": None,
            "error": {"code": "invalid_image_path"},
        })
        logger.warning("경로 이탈 시도: job_id=%s image_key=%s", job_id, image_key)
        return

    try:
        # TODO: predict_xray(image_path) 호출
        # is_pneumonia, confidence = predict_xray(image_path)
        raise NotImplementedError
    except ValueError:
        # 이미지 디코딩 실패 (worker/model.py가 이미 ValueError로 구분해줌)
        publish_result(job_id, {
            "job_id": job_id,
            "status": "failed",
            "result": None,
            "error": {"code": "invalid_xray_image"},
        })
        logger.warning("이미지 처리 실패: job_id=%s", job_id)
        return
    except Exception:
        publish_result(job_id, {
            "job_id": job_id,
            "status": "failed",
            "result": None,
            "error": {"code": "prediction_failed"},
        })
        logger.exception("추론 실패: job_id=%s", job_id)
        return

    publish_result(job_id, {
        "job_id": job_id,
        "status": "succeeded",
        "result": {
            "is_pneumonia": is_pneumonia,
            "confidence": confidence,
            "heatmap_url": None,
            "model_name": MODEL_NAME,
        },
        "error": None,
    })
    logger.info("작업 완료: job_id=%s", job_id)


def main() -> None:
    logger.info("AI worker 시작 — 모델 미리 로딩 중...")
    # 중요: FastAPI 쪽 PREDICTION_TIMEOUT_SECONDS 기본값이 2.5초로 매우 짧다
    # (app/core/config.py 참고, NFR-PRED-002의 "3초 이내 응답"에 맞춘 값).
    # 첫 요청 때 모델을 로딩하면 이 타임아웃을 거의 확실히 넘긴다.
    # 반드시 큐를 받기 전에 미리 한 번 로드해서 프로세스 메모리에 캐싱해둘 것.
    load_model()
    logger.info("모델 로딩 완료 — 큐 대기 중...")
    # TODO: 무한 루프
    # while True:
    #     task_raw = pop_next_task()
    #     if task_raw is None:
    #         continue  # BLPOP timeout, 그냥 다시 대기
    #     task = json.loads(task_raw[1])  # pop_next_task는 (key, value) 튜플 또는 None
    #     handle_task(task)
    #
    # (선택 항목, 시간 되면):
    # - 비정상 종료 시 처리 중이던 작업 복구: BLPOP 대신 BRPOPLPUSH로
    #   "processing" 리스트에 옮겨두고, 완료 후 그 리스트에서 제거하는 방식 고려
    # - 여러 워커 컨테이너를 동시에 띄워 BLPOP이 서로 겹치지 않는지 눈으로 확인
    raise NotImplementedError


if __name__ == "__main__":
    main()
