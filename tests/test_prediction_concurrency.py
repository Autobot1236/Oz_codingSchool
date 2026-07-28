import asyncio
import unittest
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.models.ai_analysis_result import AIAnalysisResult
from app.services import prediction_service


MODEL_NAME = "simple-cnn-state-dict-v1"
JOB_ID = "550e8400-e29b-41d4-a716-446655440000"


def make_prediction(
    *,
    prediction_id: int = 101,
    record_id: int = 10,
) -> AIAnalysisResult:
    return AIAnalysisResult(
        id=prediction_id,
        record_id=record_id,
        is_pneumonia=True,
        confidence=Decimal("92.35"),
        heatmap_url=None,
        ai_model=MODEL_NAME,
        created_at=datetime(2026, 7, 28, 18, 0, 0),
    )


def make_worker_response() -> prediction_service.WorkerPredictionResponse:
    return prediction_service.WorkerPredictionResponse(
        job_id=JOB_ID,
        status="succeeded",
        result={
            "is_pneumonia": True,
            "confidence": 92.35,
            "heatmap_url": None,
            "model_name": MODEL_NAME,
        },
        error=None,
    )


class PredictionConcurrencyContractTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_two_cache_misses_converge_on_one_prediction(self) -> None:
        """Two simultaneous cache misses may infer twice but must return one DB row."""
        sessions = [AsyncMock(name="session_a"), AsyncMock(name="session_b")]
        winning_prediction = make_prediction()
        worker_response = make_worker_response()

        with (
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_medical_record_by_id",
                new_callable=AsyncMock,
                return_value=object(),
            ) as get_record,
            patch(
                "app.services.prediction_service.get_cached_prediction",
                new_callable=AsyncMock,
                side_effect=[None, None],
            ) as get_cache,
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_first_xray_image",
                new_callable=AsyncMock,
                return_value=SimpleNamespace(
                    image_url="/media/xray/concurrency-test.png"
                ),
            ) as get_xray,
            patch(
                "app.services.prediction_service.resolve_xray_image_key",
                return_value="xray/concurrency-test.png",
            ) as resolve_key,
            patch(
                "app.services.prediction_service.request_worker_prediction",
                new_callable=AsyncMock,
                side_effect=[worker_response, worker_response],
            ) as request_worker,
            patch(
                "app.services.prediction_service.save_prediction_result",
                new_callable=AsyncMock,
                side_effect=[
                    (winning_prediction, False),
                    (winning_prediction, True),
                ],
            ) as save_prediction,
        ):
            results = await asyncio.gather(
                prediction_service.predict_pneumonia(sessions[0], 10),
                prediction_service.predict_pneumonia(sessions[1], 10),
            )

        self.assertEqual(get_record.await_count, 2)
        self.assertEqual(get_cache.await_count, 2)
        self.assertEqual(get_xray.await_count, 2)
        self.assertEqual(resolve_key.call_count, 2)
        self.assertEqual(request_worker.await_count, 2)
        self.assertEqual(save_prediction.await_count, 2)

        self.assertEqual({result["id"] for result in results}, {101})
        self.assertEqual({result["record_id"] for result in results}, {10})
        self.assertEqual(
            sorted(result["cached"] for result in results),
            [False, True],
        )

        for worker_call in request_worker.await_args_list:
            self.assertEqual(
                worker_call.kwargs,
                {
                    "record_id": 10,
                    "image_key": "xray/concurrency-test.png",
                    "model_name": MODEL_NAME,
                },
            )

        for save_call in save_prediction.await_args_list:
            self.assertIs(save_call.args[0] in sessions, True)
            self.assertEqual(
                save_call.kwargs,
                {
                    "record_id": 10,
                    "is_pneumonia": True,
                    "confidence": 92.35,
                    "ai_model": MODEL_NAME,
                    "heatmap_url": None,
                },
            )

    async def test_shared_cache_skips_all_worker_jobs(self) -> None:
        """Once a prediction exists, concurrent reads must not enqueue Worker jobs."""
        sessions = [AsyncMock(name="session_a"), AsyncMock(name="session_b")]
        cached_prediction = make_prediction()

        with (
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_medical_record_by_id",
                new_callable=AsyncMock,
                return_value=object(),
            ),
            patch(
                "app.services.prediction_service.get_cached_prediction",
                new_callable=AsyncMock,
                side_effect=[cached_prediction, cached_prediction],
            ),
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_first_xray_image",
                new_callable=AsyncMock,
            ) as get_xray,
            patch(
                "app.services.prediction_service.request_worker_prediction",
                new_callable=AsyncMock,
            ) as request_worker,
            patch(
                "app.services.prediction_service.save_prediction_result",
                new_callable=AsyncMock,
            ) as save_prediction,
        ):
            results = await asyncio.gather(
                prediction_service.predict_pneumonia(sessions[0], 10),
                prediction_service.predict_pneumonia(sessions[1], 10),
            )

        self.assertEqual({result["id"] for result in results}, {101})
        self.assertTrue(all(result["cached"] for result in results))
        get_xray.assert_not_awaited()
        request_worker.assert_not_awaited()
        save_prediction.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
