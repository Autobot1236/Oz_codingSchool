from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis_result import AIAnalysisResult
from app.repositories import prediction_repository

CONFIDENCE_QUANTUM = Decimal("0.01")
MIN_CONFIDENCE = Decimal("0.00")
MAX_CONFIDENCE = Decimal("100.00")
MAX_AI_MODEL_LENGTH = 50
MAX_HEATMAP_URL_LENGTH = 255


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
