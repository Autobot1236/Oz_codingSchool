import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, ValidationError, model_validator
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.models.ai_analysis_result import AIAnalysisResult
from app.repositories import prediction_repository
from worker.model import MODEL_NAME

logger = logging.getLogger(__name__)

CONFIDENCE_QUANTUM = Decimal("0.01")
MIN_CONFIDENCE = Decimal("0.00")
MAX_CONFIDENCE = Decimal("100.00")
MAX_AI_MODEL_LENGTH = 50
MAX_HEATMAP_URL_LENGTH = 255
PROJECT_ROOT = Path(__file__).resolve().parents[2]
XRAY_MEDIA_ROOT = (PROJECT_ROOT / "media" / "xray").resolve()

PREDICTION_ACCESS_DENIED_DETAIL = "prediction_access_denied"
MEDICAL_RECORD_NOT_FOUND_DETAIL = "medical_record_not_found"
XRAY_IMAGE_NOT_FOUND_DETAIL = "xray_image_not_found"
INVALID_XRAY_IMAGE_DETAIL = "invalid_xray_image"
MODEL_UNAVAILABLE_DETAIL = "model_unavailable"
PREDICTION_FAILED_DETAIL = "prediction_failed"
INVALID_IMAGE_PATH_DETAIL = "invalid_image_path"
PREDICTION_QUEUE_UNAVAILABLE_DETAIL = "prediction_queue_unavailable"
PREDICTION_TIMEOUT_DETAIL = "prediction_timeout"

WORKER_ERROR_STATUS = {
    INVALID_IMAGE_PATH_DETAIL: status.HTTP_500_INTERNAL_SERVER_ERROR,
    XRAY_IMAGE_NOT_FOUND_DETAIL: status.HTTP_404_NOT_FOUND,
    INVALID_XRAY_IMAGE_DETAIL: status.HTTP_422_UNPROCESSABLE_CONTENT,
    MODEL_UNAVAILABLE_DETAIL: status.HTTP_503_SERVICE_UNAVAILABLE,
    PREDICTION_FAILED_DETAIL: status.HTTP_500_INTERNAL_SERVER_ERROR,
}
SUBSCRIPTION_TIMEOUT_SECONDS = 1.0


class PredictionData(TypedDict):
    id: int
    record_id: int
    is_pneumonia: bool
    confidence: float
    heatmap_url: str | None
    ai_model: str
    created_at: datetime


class PredictionResult(PredictionData):
    cached: bool


class PredictionPage(TypedDict):
    predictions: list[PredictionData]
    page: int
    size: int
    total: int


class WorkerPredictionData(BaseModel):
    is_pneumonia: bool
    confidence: float = Field(ge=0.0, le=100.0)
    heatmap_url: str | None = None
    model_name: str = Field(min_length=1, max_length=MAX_AI_MODEL_LENGTH)


class WorkerPredictionError(BaseModel):
    code: Literal[
        "invalid_image_path",
        "xray_image_not_found",
        "invalid_xray_image",
        "model_unavailable",
        "prediction_failed",
    ]


class WorkerPredictionResponse(BaseModel):
    job_id: str = Field(min_length=36, max_length=36)
    status: Literal["succeeded", "failed"]
    result: WorkerPredictionData | None
    error: WorkerPredictionError | None

    @model_validator(mode="after")
    def validate_status_payload(self) -> "WorkerPredictionResponse":
        if self.status == "succeeded":
            if self.result is None or self.error is not None:
                raise ValueError("invalid_worker_success_payload")
        elif self.result is not None or self.error is None:
            raise ValueError("invalid_worker_failure_payload")
        return self


def normalize_ai_model(ai_model: str) -> str:
    normalized_ai_model = ai_model.strip()
    if not normalized_ai_model or len(normalized_ai_model) > MAX_AI_MODEL_LENGTH:
        raise ValueError("invalid_ai_model")
    return normalized_ai_model


def normalize_confidence(confidence: Decimal | float | int) -> Decimal:
    try:
        normalized_confidence = Decimal(str(confidence))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid_prediction_confidence") from exc

    if (
        not normalized_confidence.is_finite()
        or normalized_confidence < MIN_CONFIDENCE
        or normalized_confidence > MAX_CONFIDENCE
    ):
        raise ValueError("invalid_prediction_confidence")

    return normalized_confidence.quantize(
        CONFIDENCE_QUANTUM,
        rounding=ROUND_HALF_UP,
    )


def normalize_heatmap_url(heatmap_url: str | None) -> str | None:
    if heatmap_url is None:
        return None

    normalized_heatmap_url = heatmap_url.strip()
    if (
        not normalized_heatmap_url
        or len(normalized_heatmap_url) > MAX_HEATMAP_URL_LENGTH
    ):
        raise ValueError("invalid_heatmap_url")
    return normalized_heatmap_url


def to_prediction_data(
    prediction: AIAnalysisResult,
) -> PredictionData:
    return {
        "id": prediction.id,
        "record_id": prediction.record_id,
        "is_pneumonia": prediction.is_pneumonia,
        "confidence": float(prediction.confidence),
        "heatmap_url": prediction.heatmap_url,
        "ai_model": prediction.ai_model,
        "created_at": prediction.created_at,
    }


def resolve_xray_image_path(image_url: str) -> Path:
    relative_path = image_url.lstrip("/")
    media_prefix = "media/xray/"
    if not relative_path.startswith(media_prefix):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=XRAY_IMAGE_NOT_FOUND_DETAIL,
        )

    stored_path = relative_path.removeprefix(media_prefix)
    candidate_path = (XRAY_MEDIA_ROOT / stored_path).resolve()
    try:
        candidate_path.relative_to(XRAY_MEDIA_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=XRAY_IMAGE_NOT_FOUND_DETAIL,
        ) from exc

    if not candidate_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=XRAY_IMAGE_NOT_FOUND_DETAIL,
        )
    return candidate_path


def resolve_xray_image_key(image_url: str) -> str:
    image_path = resolve_xray_image_path(image_url)
    stored_path = image_path.relative_to(XRAY_MEDIA_ROOT).as_posix()
    return f"xray/{stored_path}"


def _decode_worker_response(
    raw_data: str | bytes,
    expected_job_id: str,
) -> WorkerPredictionResponse:
    try:
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")
        response = WorkerPredictionResponse.model_validate_json(raw_data)
    except (TypeError, UnicodeDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PREDICTION_FAILED_DETAIL,
        ) from exc

    if response.job_id != expected_job_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PREDICTION_FAILED_DETAIL,
        )
    return response


async def _confirm_subscription(pubsub) -> None:
    try:
        async with asyncio.timeout(SUBSCRIPTION_TIMEOUT_SECONDS):
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=False,
                    timeout=SUBSCRIPTION_TIMEOUT_SECONDS,
                )
                if message is not None and message.get("type") == "subscribe":
                    return
                await asyncio.sleep(0)
    except TimeoutError as exc:
        raise RedisError("Redis result subscription was not confirmed.") from exc


async def request_worker_prediction(
    *,
    record_id: int,
    image_key: str,
    model_name: str,
) -> WorkerPredictionResponse:
    job_id = str(uuid4())
    result_channel = (
        f"{settings.PREDICTION_RESULT_CHANNEL_PREFIX}:{job_id}"
    )
    request_payload = json.dumps(
        {
            "job_id": job_id,
            "record_id": record_id,
            "image_key": image_key,
            "model_name": model_name,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    redis_client = get_redis_client()
    pubsub = redis_client.pubsub()
    subscribed = False

    try:
        # Pub/Sub does not retain messages. Subscribe before queueing the job
        # so a fast Worker response cannot be lost.
        await pubsub.subscribe(result_channel)
        await _confirm_subscription(pubsub)
        subscribed = True
        await redis_client.rpush(
            settings.PREDICTION_QUEUE_NAME,
            request_payload,
        )

        async with asyncio.timeout(settings.PREDICTION_TIMEOUT_SECONDS):
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=settings.PREDICTION_TIMEOUT_SECONDS,
                )
                if message is None:
                    await asyncio.sleep(0)
                    continue
                return _decode_worker_response(
                    message["data"],
                    job_id,
                )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=PREDICTION_TIMEOUT_DETAIL,
        ) from exc
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PREDICTION_QUEUE_UNAVAILABLE_DETAIL,
        ) from exc
    finally:
        if subscribed:
            try:
                await pubsub.unsubscribe(result_channel)
            except RedisError:
                logger.warning(
                    "Redis 결과 채널 구독 해제에 실패했습니다: %s",
                    result_channel,
                    exc_info=True,
                )
        try:
            await pubsub.aclose()
        except RedisError:
            logger.warning(
                "Redis Pub/Sub 연결 종료에 실패했습니다.",
                exc_info=True,
            )


def raise_worker_error(error_code: str) -> None:
    status_code = WORKER_ERROR_STATUS.get(
        error_code,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    detail = (
        error_code
        if error_code in WORKER_ERROR_STATUS
        else PREDICTION_FAILED_DETAIL
    )
    raise HTTPException(status_code=status_code, detail=detail)


async def get_cached_prediction(
    session: AsyncSession,
    record_id: int,
    ai_model: str,
) -> AIAnalysisResult | None:
    return await prediction_repository.get_prediction_by_record_and_model(
        session,
        record_id,
        normalize_ai_model(ai_model),
    )


async def save_prediction_result(
    session: AsyncSession,
    *,
    record_id: int,
    is_pneumonia: bool,
    confidence: Decimal | float | int,
    ai_model: str,
    heatmap_url: str | None = None,
) -> tuple[AIAnalysisResult, bool]:
    normalized_ai_model = normalize_ai_model(ai_model)
    prediction = AIAnalysisResult(
        record_id=record_id,
        is_pneumonia=is_pneumonia,
        confidence=normalize_confidence(confidence),
        heatmap_url=normalize_heatmap_url(heatmap_url),
        ai_model=normalized_ai_model,
    )
    prediction_repository.add_prediction(session, prediction)

    try:
        await session.commit()
        await session.refresh(prediction)
    except IntegrityError:
        await session.rollback()
        cached_prediction = (
            await prediction_repository.get_prediction_by_record_and_model(
                session,
                record_id,
                normalized_ai_model,
            )
        )
        if cached_prediction is not None:
            return cached_prediction, True
        raise
    except Exception:
        await session.rollback()
        raise

    return prediction, False


async def list_prediction_results(
    session: AsyncSession,
    *,
    record_id: int,
    page: int,
    size: int,
) -> tuple[list[AIAnalysisResult], int]:
    return await prediction_repository.list_predictions(
        session,
        record_id,
        page,
        size,
    )


async def predict_pneumonia(
    session: AsyncSession,
    record_id: int,
) -> PredictionResult:
    """Run or reuse a prediction after Router-level access control."""
    medical_record = await prediction_repository.get_medical_record_by_id(
        session,
        record_id,
    )
    if medical_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MEDICAL_RECORD_NOT_FOUND_DETAIL,
        )

    cached_prediction = await get_cached_prediction(
        session,
        record_id,
        MODEL_NAME,
    )
    if cached_prediction is not None:
        return {
            **to_prediction_data(cached_prediction),
            "cached": True,
        }

    xray_image = await prediction_repository.get_first_xray_image(
        session,
        record_id,
    )
    if xray_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=XRAY_IMAGE_NOT_FOUND_DETAIL,
        )

    image_key = resolve_xray_image_key(xray_image.image_url)
    worker_response = await request_worker_prediction(
        record_id=record_id,
        image_key=image_key,
        model_name=MODEL_NAME,
    )

    if worker_response.status == "failed":
        if worker_response.error is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=PREDICTION_FAILED_DETAIL,
            )
        raise_worker_error(worker_response.error.code)

    worker_result = worker_response.result
    if worker_result is None or worker_result.model_name != MODEL_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PREDICTION_FAILED_DETAIL,
        )

    try:
        prediction, cached = await save_prediction_result(
            session,
            record_id=record_id,
            is_pneumonia=worker_result.is_pneumonia,
            confidence=worker_result.confidence,
            ai_model=worker_result.model_name,
            heatmap_url=worker_result.heatmap_url,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PREDICTION_FAILED_DETAIL,
        ) from exc

    return {
        **to_prediction_data(prediction),
        "cached": cached,
    }


async def get_predictions(
    session: AsyncSession,
    record_id: int,
    page: int,
    size: int,
) -> PredictionPage:
    medical_record = await prediction_repository.get_medical_record_by_id(
        session,
        record_id,
    )
    if medical_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MEDICAL_RECORD_NOT_FOUND_DETAIL,
        )

    predictions, total = await list_prediction_results(
        session,
        record_id=record_id,
        page=page,
        size=size,
    )
    return {
        "predictions": [
            to_prediction_data(prediction)
            for prediction in predictions
        ],
        "page": page,
        "size": size,
        "total": total,
    }
