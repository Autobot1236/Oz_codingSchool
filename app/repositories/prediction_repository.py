from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis_result import AIAnalysisResult


async def get_prediction_by_record_and_model(
    session: AsyncSession,
    record_id: int,
    ai_model: str,
) -> AIAnalysisResult | None:
    result = await session.execute(
        select(AIAnalysisResult).where(
            AIAnalysisResult.record_id == record_id,
            AIAnalysisResult.ai_model == ai_model,
        )
    )
    return result.scalar_one_or_none()


async def list_predictions(
    session: AsyncSession,
    record_id: int,
    page: int,
    size: int,
) -> tuple[list[AIAnalysisResult], int]:
    predictions_result = await session.execute(
        select(AIAnalysisResult)
        .where(AIAnalysisResult.record_id == record_id)
        .order_by(
            AIAnalysisResult.created_at.desc(),
            AIAnalysisResult.id.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    total_result = await session.execute(
        select(func.count(AIAnalysisResult.id)).where(
            AIAnalysisResult.record_id == record_id
        )
    )
    return (
        list(predictions_result.scalars().all()),
        total_result.scalar_one(),
    )


def add_prediction(
    session: AsyncSession,
    prediction: AIAnalysisResult,
) -> None:
    session.add(prediction)
