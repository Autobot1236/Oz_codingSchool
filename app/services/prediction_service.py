from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import TypedDict

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis_result import AIAnalysisResult
from app.repositories import prediction_repository
from worker.model import MODEL_NAME, load_model, predict_xray

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
MODEL_UNAVAILABLE_DETAIL = "model_unavailable"
PREDICTION_FAILED_DETAIL = "prediction_failed"


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

    image_path = resolve_xray_image_path(xray_image.image_url)

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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PREDICTION_FAILED_DETAIL,
        ) from exc

    try:
        prediction, cached = await save_prediction_result(
            session,
            record_id=record_id,
            is_pneumonia=is_pneumonia,
            confidence=confidence,
            ai_model=MODEL_NAME,
            heatmap_url=None,
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
