import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy.exc import IntegrityError

from app.models.ai_analysis_result import AIAnalysisResult
from app.services import prediction_service

NOW = datetime(2026, 7, 27, 10, 30, 0)
MODEL_NAME = "simple-cnn-state-dict-v1"


def make_prediction(prediction_id: int = 1) -> AIAnalysisResult:
    return AIAnalysisResult(
        id=prediction_id,
        record_id=10,
        is_pneumonia=True,
        confidence=Decimal("94.28"),
        heagit status --short
git diff --cached --name-status
git diff --cached --checktmap_url=None,
        ai_model=MODEL_NAME,
        created_at=NOW,
    )


class AIAnalysisResultModelTestCase(unittest.TestCase):
    def test_cache_constraint_and_list_index_are_declared(self) -> None:
        table = AIAnalysisResult.__table__
        unique_constraint = next(
            constraint
            for constraint in table.constraints
            if constraint.name == "uq_ai_analysis_results_record_model"
        )
        list_index = next(
            index
            for index in table.indexes
            if index.name == "ix_ai_analysis_results_record_created_at"
        )

        self.assertEqual(
            [column.name for column in unique_constraint.columns],
            ["record_id", "ai_model"],
        )
        self.assertEqual(
            [column.name for column in list_index.columns],
            ["record_id", "created_at"],
        )
        self.assertTrue(table.c.heatmap_url.nullable)
        self.assertFalse(table.c.confidence.nullable)


class PredictionStorageServiceTestCase(unittest.IsolatedAsyncioTestCase):
    def test_normalize_confidence_uses_percent_and_two_decimals(self) -> None:
        self.assertEqual(
            prediction_service.normalize_confidence(94.285),
            Decimal("94.29"),
        )
        self.assertEqual(
            prediction_service.normalize_confidence(0),
            Decimal("0.00"),
        )
        self.assertEqual(
            prediction_service.normalize_confidence(100),
            Decimal("100.00"),
        )

    def test_normalize_confidence_rejects_invalid_values(self) -> None:
        for invalid_value in (-0.01, 100.01, float("nan"), float("inf")):
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaisesRegex(
                    ValueError,
                    "invalid_prediction_confidence",
                ):
                    prediction_service.normalize_confidence(invalid_value)

    async def test_get_cached_prediction_uses_record_and_model_key(self) -> None:
        session = AsyncMock()
        cached_prediction = make_prediction()

        with patch(
            "app.services.prediction_service.prediction_repository."
            "get_prediction_by_record_and_model",
            new_callable=AsyncMock,
            return_value=cached_prediction,
        ) as get_prediction:
            result = await prediction_service.get_cached_prediction(
                session,
                record_id=10,
                ai_model=f" {MODEL_NAME} ",
            )

        self.assertIs(result, cached_prediction)
        get_prediction.assert_awaited_once_with(
            session,
            10,
            MODEL_NAME,
        )

    async def test_save_prediction_commits_new_result(self) -> None:
        session = AsyncMock()

        with patch(
            "app.services.prediction_service.prediction_repository.add_prediction"
        ) as add_prediction:
            result, cached = await prediction_service.save_prediction_result(
                session,
                record_id=10,
                is_pneumonia=True,
                confidence=94.285,
                ai_model=MODEL_NAME,
            )

        self.assertFalse(cached)
        self.assertEqual(result.record_id, 10)
        self.assertEqual(result.confidence, Decimal("94.29"))
        self.assertIsNone(result.heatmap_url)
        add_prediction.assert_called_once_with(session, result)
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(result)
        session.rollback.assert_not_awaited()

    async def test_unique_conflict_returns_winning_cached_result(self) -> None:
        session = AsyncMock()
        session.commit.side_effect = IntegrityError(
            "INSERT ai_analysis_results",
            {},
            Exception("duplicate cache key"),
        )
        cached_prediction = make_prediction(prediction_id=2)

        with (
            patch(
                "app.services.prediction_service.prediction_repository."
                "add_prediction"
            ),
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_prediction_by_record_and_model",
                new_callable=AsyncMock,
                return_value=cached_prediction,
            ) as get_prediction,
        ):
            result, cached = await prediction_service.save_prediction_result(
                session,
                record_id=10,
                is_pneumonia=True,
                confidence=94.28,
                ai_model=MODEL_NAME,
            )

        self.assertTrue(cached)
        self.assertIs(result, cached_prediction)
        session.rollback.assert_awaited_once()
        get_prediction.assert_awaited_once_with(
            session,
            10,
            MODEL_NAME,
        )

    async def test_unique_conflict_without_winner_is_reraised(self) -> None:
        session = AsyncMock()
        integrity_error = IntegrityError(
            "INSERT ai_analysis_results",
            {},
            Exception("unexpected integrity error"),
        )
        session.commit.side_effect = integrity_error

        with (
            patch(
                "app.services.prediction_service.prediction_repository."
                "add_prediction"
            ),
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_prediction_by_record_and_model",
                new_callable=AsyncMock,
                return_value=None,
            ),
            self.assertRaises(IntegrityError),
        ):
            await prediction_service.save_prediction_result(
                session,
                record_id=10,
                is_pneumonia=True,
                confidence=94.28,
                ai_model=MODEL_NAME,
            )

        session.rollback.assert_awaited_once()

    async def test_unexpected_save_error_rolls_back(self) -> None:
        session = AsyncMock()
        session.commit.side_effect = RuntimeError("database unavailable")

        with (
            patch(
                "app.services.prediction_service.prediction_repository."
                "add_prediction"
            ),
            self.assertRaises(RuntimeError),
        ):
            await prediction_service.save_prediction_result(
                session,
                record_id=10,
                is_pneumonia=False,
                confidence=87.1,
                ai_model=MODEL_NAME,
            )

        session.rollback.assert_awaited_once()

    async def test_list_prediction_results_delegates_pagination(self) -> None:
        session = AsyncMock()
        predictions = [make_prediction()]

        with patch(
            "app.services.prediction_service.prediction_repository."
            "list_predictions",
            new_callable=AsyncMock,
            return_value=(predictions, 1),
        ) as list_predictions:
            result = await prediction_service.list_prediction_results(
                session,
                record_id=10,
                page=1,
                size=10,
            )

        self.assertEqual(result, (predictions, 1))
        list_predictions.assert_awaited_once_with(
            session,
            10,
            1,
            10,
        )


if __name__ == "__main__":
    unittest.main()
