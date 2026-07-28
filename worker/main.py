"""AI worker: consume Redis jobs, run inference, and publish one result."""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from worker.model import MODEL_NAME, load_model, predict_xray
from worker.redis_client import pop_next_task, publish_result

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("ai-worker")

MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/app/media")).resolve()


class InvalidImagePathError(Exception):
    """The supplied image key does not resolve safely below MEDIA_ROOT."""


class XrayImageNotFoundError(Exception):
    """The X-ray image does not exist in the shared media volume."""


class InvalidXrayImageError(Exception):
    """The X-ray file cannot be decoded as an image."""


class ModelUnavailableError(Exception):
    """The configured inference model cannot be loaded or selected."""


class InvalidJobPayloadError(Exception):
    """The Redis job does not satisfy the worker input contract."""


_model_unavailable = False


def preload_model() -> None:
    """Load the model once during worker startup to avoid first-job latency."""
    global _model_unavailable
    try:
        load_model()
    except Exception as exc:
        _model_unavailable = True
        logger.exception("모델 사전 로딩 실패")
        raise ModelUnavailableError from exc
    else:
        _model_unavailable = False
        logger.info("모델 사전 로딩 완료: model_name=%s", MODEL_NAME)


def _validated_job_id(task: dict[str, Any]) -> str:
    value = task.get("job_id")
    if not isinstance(value, str):
        raise InvalidJobPayloadError("job_id must be a UUID string.")
    try:
        UUID(value)
    except ValueError as exc:
        raise InvalidJobPayloadError("job_id must be a UUID string.") from exc
    return value


def _validate_task(task: dict[str, Any]) -> tuple[str, int, str, str]:
    job_id = _validated_job_id(task)

    record_id = task.get("record_id")
    if isinstance(record_id, bool) or not isinstance(record_id, int):
        raise InvalidJobPayloadError("record_id must be an integer.")

    image_key = task.get("image_key")
    if not isinstance(image_key, str):
        raise InvalidImagePathError

    model_name = task.get("model_name")
    if not isinstance(model_name, str):
        raise InvalidJobPayloadError("model_name must be a string.")

    return job_id, record_id, image_key, model_name


def resolve_image_path(image_key: str) -> Path:
    """Validate an image key and resolve it inside the shared media root."""
    key_path = Path(image_key)
    if (
        not image_key.startswith("xray/")
        or key_path.is_absolute()
        or ".." in key_path.parts
    ):
        raise InvalidImagePathError

    image_path = (MEDIA_ROOT / key_path).resolve()
    try:
        image_path.relative_to(MEDIA_ROOT)
    except ValueError as exc:
        raise InvalidImagePathError from exc

    if not image_path.is_file():
        raise XrayImageNotFoundError
    return image_path


def _success_payload(
    job_id: str,
    is_pneumonia: bool,
    confidence: float,
    model_name: str,
) -> dict[str, Any]:
    if not isinstance(is_pneumonia, bool):
        raise ValueError("Prediction class must be boolean.")

    confidence = round(float(confidence), 2)
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 100.0:
        raise ValueError("Prediction confidence is outside the allowed range.")

    return {
        "job_id": job_id,
        "status": "succeeded",
        "result": {
            "is_pneumonia": is_pneumonia,
            "confidence": confidence,
            "heatmap_url": None,
            "model_name": model_name,
        },
        "error": None,
    }


def _failure_payload(job_id: str, code: str) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "status": "failed",
        "result": None,
        "error": {"code": code},
    }


def handle_task(task: dict[str, Any]) -> None:
    """Process one job and publish exactly one success or failure payload."""
    raw_job_id = task.get("job_id")
    job_id = raw_job_id if isinstance(raw_job_id, str) else None

    try:
        job_id, record_id, image_key, model_name = _validate_task(task)
        logger.info("작업 시작: job_id=%s record_id=%s", job_id, record_id)

        if _model_unavailable or model_name != MODEL_NAME:
            raise ModelUnavailableError

        image_path = resolve_image_path(image_key)
        try:
            is_pneumonia, confidence = predict_xray(image_path)
        except ValueError as exc:
            raise InvalidXrayImageError from exc

        payload = _success_payload(
            job_id,
            is_pneumonia,
            confidence,
            model_name,
        )
    except InvalidImagePathError:
        code = "invalid_image_path"
        payload = _failure_payload(job_id, code) if job_id else None
        logger.exception("잘못된 이미지 경로: job_id=%s", job_id)
    except XrayImageNotFoundError:
        code = "xray_image_not_found"
        payload = _failure_payload(job_id, code) if job_id else None
        logger.exception("X-ray 이미지 없음: job_id=%s", job_id)
    except InvalidXrayImageError:
        code = "invalid_xray_image"
        payload = _failure_payload(job_id, code) if job_id else None
        logger.exception("X-ray 이미지 디코딩 실패: job_id=%s", job_id)
    except ModelUnavailableError:
        code = "model_unavailable"
        payload = _failure_payload(job_id, code) if job_id else None
        logger.exception("모델 사용 불가: job_id=%s", job_id)
    except Exception:
        code = "prediction_failed"
        payload = _failure_payload(job_id, code) if job_id else None
        logger.exception("추론 실패: job_id=%s", job_id)

    if payload is None:
        logger.error("유효한 job_id가 없어 결과를 발행할 수 없음")
        return

    try:
        publish_result(job_id, payload)
    except Exception:
        logger.exception("결과 발행 실패: job_id=%s", job_id)
        return

    if payload["status"] == "succeeded":
        logger.info("작업 완료: job_id=%s", job_id)
    else:
        logger.warning(
            "작업 실패 결과 발행: job_id=%s error_code=%s",
            job_id,
            payload["error"]["code"],
        )


def main() -> None:
    """Preload the model and continuously consume prediction jobs."""
    logger.info("AI worker 시작")
    try:
        preload_model()
    except ModelUnavailableError:
        logger.error("모델 없이 큐를 처리하며 model_unavailable을 반환함")

    logger.info("큐 대기 중")
    while True:
        try:
            task = pop_next_task()
        except Exception:
            logger.exception("Redis 작업 수신 실패")
            continue

        if task is not None:
            handle_task(task)


if __name__ == "__main__":
    main()
