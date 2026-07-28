import tempfile
import unittest
from json import dumps
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch
from uuid import UUID

from fastapi import HTTPException
from redis.exceptions import RedisError
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
        heatmap_url=None,
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


class PredictionRedisContractTestCase(unittest.IsolatedAsyncioTestCase):
    def make_redis_mocks(self):
        redis_client = MagicMock()
        pubsub = MagicMock()
        redis_client.pubsub.return_value = pubsub
        redis_client.rpush = AsyncMock()
        pubsub.subscribe = AsyncMock()
        pubsub.unsubscribe = AsyncMock()
        pubsub.aclose = AsyncMock()
        pubsub.get_message = AsyncMock(
            return_value={"type": "subscribe"}
        )
        return redis_client, pubsub

    async def test_subscribes_before_enqueue_and_validates_result(self) -> None:
        redis_client, pubsub = self.make_redis_mocks()
        job_id = "550e8400-e29b-41d4-a716-446655440000"
        result_channel = f"prediction:results:{job_id}"
        pubsub.get_message = AsyncMock(
            side_effect=[
                {"type": "subscribe"},
                {
                    "type": "message",
                    "data": dumps(
                        {
                            "job_id": job_id,
                            "status": "succeeded",
                            "result": {
                                "is_pneumonia": True,
                                "confidence": 92.35,
                                "heatmap_url": None,
                                "model_name": MODEL_NAME,
                            },
                            "error": None,
                        }
                    ),
                },
            ]
        )
        operations = MagicMock()
        operations.attach_mock(pubsub.subscribe, "subscribe")
        operations.attach_mock(redis_client.rpush, "rpush")

        with (
            patch(
                "app.services.prediction_service.get_redis_client",
                return_value=redis_client,
            ),
            patch(
                "app.services.prediction_service.uuid4",
                return_value=UUID(job_id),
            ),
        ):
            response = await prediction_service.request_worker_prediction(
                record_id=10,
                image_key="xray/test.png",
                model_name=MODEL_NAME,
            )

        self.assertEqual(response.status, "succeeded")
        self.assertTrue(response.result.is_pneumonia)
        self.assertEqual(
            operations.method_calls[:2],
            [
                call.subscribe(result_channel),
                call.rpush(
                    "prediction:jobs",
                    ANY,
                ),
            ],
        )
        queued_payload = redis_client.rpush.await_args.args[1]
        self.assertIn('"image_key":"xray/test.png"', queued_payload)
        pubsub.unsubscribe.assert_awaited_once_with(result_channel)
        pubsub.aclose.assert_awaited_once_with()

    async def test_maps_redis_error_to_service_unavailable(self) -> None:
        redis_client, pubsub = self.make_redis_mocks()
        redis_client.rpush.side_effect = RedisError("redis unavailable")

        with (
            patch(
                "app.services.prediction_service.get_redis_client",
                return_value=redis_client,
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await prediction_service.request_worker_prediction(
                record_id=10,
                image_key="xray/test.png",
                model_name=MODEL_NAME,
            )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail,
            "prediction_queue_unavailable",
        )
        pubsub.unsubscribe.assert_awaited_once()
        pubsub.aclose.assert_awaited_once_with()

    async def test_maps_worker_timeout_to_gateway_timeout(self) -> None:
        redis_client, pubsub = self.make_redis_mocks()
        pubsub.get_message = AsyncMock(
            side_effect=[
                {"type": "subscribe"},
                *([None] * 100),
            ]
        )

        with (
            patch(
                "app.services.prediction_service.get_redis_client",
                return_value=redis_client,
            ),
            patch.object(
                prediction_service.settings,
                "PREDICTION_TIMEOUT_SECONDS",
                0.001,
            ),
            self.assertRaises(HTTPException) as raised,
        ):
            await prediction_service.request_worker_prediction(
                record_id=10,
                image_key="xray/test.png",
                model_name=MODEL_NAME,
            )

        self.assertEqual(raised.exception.status_code, 504)
        self.assertEqual(raised.exception.detail, "prediction_timeout")

    def test_rejects_malformed_or_mismatched_worker_response(self) -> None:
        for raw_data in (
            "not-json",
            dumps(
                {
                    "job_id": "different-job",
                    "status": "failed",
                    "result": None,
                    "error": {"code": "prediction_failed"},
                }
            ),
        ):
            with self.subTest(raw_data=raw_data):
                with self.assertRaises(HTTPException) as raised:
                    prediction_service._decode_worker_response(
                        raw_data,
                        "expected-job",
                    )
                self.assertEqual(raised.exception.status_code, 500)
                self.assertEqual(
                    raised.exception.detail,
                    "prediction_failed",
                )


class PredictionPublicContractTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_predict_pneumonia_runs_first_prediction(self) -> None:
        session = AsyncMock()
        prediction = make_prediction()
        xray_image = SimpleNamespace(image_url="/media/xray/test.png")

        with tempfile.TemporaryDirectory(
            dir=Path.cwd(),
            prefix="prediction-test-",
        ) as temporary_directory:
            media_root = Path(temporary_directory).resolve()
            image_path = media_root / "test.png"
            image_path.write_bytes(b"synthetic-xray")

            with (
                patch.object(
                    prediction_service,
                    "XRAY_MEDIA_ROOT",
                    media_root,
                ),
                patch(
                    "app.services.prediction_service.prediction_repository."
                    "get_medical_record_by_id",
                    new_callable=AsyncMock,
                    return_value=object(),
                ),
                patch(
                    "app.services.prediction_service.get_cached_prediction",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
                patch(
                    "app.services.prediction_service.prediction_repository."
                    "get_first_xray_image",
                    new_callable=AsyncMock,
                    return_value=xray_image,
                ),
                patch(
                    "app.services.prediction_service."
                    "request_worker_prediction",
                    new_callable=AsyncMock,
                    return_value=prediction_service.WorkerPredictionResponse(
                        job_id="550e8400-e29b-41d4-a716-446655440000",
                        status="succeeded",
                        result={
                            "is_pneumonia": True,
                            "confidence": 94.28,
                            "heatmap_url": None,
                            "model_name": MODEL_NAME,
                        },
                        error=None,
                    ),
                ) as request_worker,
                patch(
                    "app.services.prediction_service.save_prediction_result",
                    new_callable=AsyncMock,
                    return_value=(prediction, False),
                ) as save_prediction,
            ):
                result = await prediction_service.predict_pneumonia(
                    session,
                    10,
                )

        self.assertFalse(result["cached"])
        self.assertEqual(result["record_id"], 10)
        self.assertEqual(result["confidence"], 94.28)
        request_worker.assert_awaited_once_with(
            record_id=10,
            image_key="xray/test.png",
            model_name=MODEL_NAME,
        )
        save_prediction.assert_awaited_once_with(
            session,
            record_id=10,
            is_pneumonia=True,
            confidence=94.28,
            ai_model=MODEL_NAME,
            heatmap_url=None,
        )

    async def test_predict_pneumonia_reuses_cached_result(self) -> None:
        session = AsyncMock()
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
                return_value=cached_prediction,
            ),
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_first_xray_image",
                new_callable=AsyncMock,
            ) as get_xray_image,
            patch(
                "app.services.prediction_service.request_worker_prediction",
                new_callable=AsyncMock,
            ) as request_worker,
        ):
            result = await prediction_service.predict_pneumonia(
                session,
                10,
            )

        self.assertTrue(result["cached"])
        self.assertEqual(result["id"], cached_prediction.id)
        get_xray_image.assert_not_awaited()
        request_worker.assert_not_awaited()

    async def test_predict_pneumonia_rejects_missing_record(self) -> None:
        session = AsyncMock()
        with patch(
            "app.services.prediction_service.prediction_repository."
            "get_medical_record_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as raised:
                await prediction_service.predict_pneumonia(session, 999)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(
            raised.exception.detail,
            "medical_record_not_found",
        )

    async def test_predict_pneumonia_rejects_missing_xray(self) -> None:
        session = AsyncMock()
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
                return_value=None,
            ),
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_first_xray_image",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await prediction_service.predict_pneumonia(session, 10)

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "xray_image_not_found")

    async def test_predict_pneumonia_maps_model_load_error(self) -> None:
        session = AsyncMock()

        with tempfile.TemporaryDirectory(
            dir=Path.cwd(),
            prefix="prediction-test-",
        ) as temporary_directory:
            media_root = Path(temporary_directory).resolve()
            (media_root / "test.png").write_bytes(b"synthetic-xray")

            with (
                patch.object(
                    prediction_service,
                    "XRAY_MEDIA_ROOT",
                    media_root,
                ),
                patch(
                    "app.services.prediction_service.prediction_repository."
                    "get_medical_record_by_id",
                    new_callable=AsyncMock,
                    return_value=object(),
                ),
                patch(
                    "app.services.prediction_service.get_cached_prediction",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
                patch(
                    "app.services.prediction_service.prediction_repository."
                    "get_first_xray_image",
                    new_callable=AsyncMock,
                    return_value=SimpleNamespace(
                        image_url="/media/xray/test.png"
                    ),
                ),
                patch(
                    "app.services.prediction_service."
                    "request_worker_prediction",
                    new_callable=AsyncMock,
                    return_value=prediction_service.WorkerPredictionResponse(
                        job_id="550e8400-e29b-41d4-a716-446655440000",
                        status="failed",
                        result=None,
                        error={"code": "model_unavailable"},
                    ),
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await prediction_service.predict_pneumonia(
                        session,
                        10,
                    )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "model_unavailable")

    async def test_predict_pneumonia_maps_invalid_xray_image_error(self) -> None:
        session = AsyncMock()

        with tempfile.TemporaryDirectory(
            dir=Path.cwd(),
            prefix="prediction-test-",
        ) as temporary_directory:
            media_root = Path(temporary_directory).resolve()
            (media_root / "test.png").write_bytes(b"synthetic-xray")

            with (
                patch.object(
                    prediction_service,
                    "XRAY_MEDIA_ROOT",
                    media_root,
                ),
                patch(
                    "app.services.prediction_service.prediction_repository."
                    "get_medical_record_by_id",
                    new_callable=AsyncMock,
                    return_value=object(),
                ),
                patch(
                    "app.services.prediction_service.get_cached_prediction",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
                patch(
                    "app.services.prediction_service.prediction_repository."
                    "get_first_xray_image",
                    new_callable=AsyncMock,
                    return_value=SimpleNamespace(
                        image_url="/media/xray/test.png"
                    ),
                ),
                patch(
                    "app.services.prediction_service."
                    "request_worker_prediction",
                    new_callable=AsyncMock,
                    return_value=prediction_service.WorkerPredictionResponse(
                        job_id="550e8400-e29b-41d4-a716-446655440000",
                        status="failed",
                        result=None,
                        error={"code": "invalid_xray_image"},
                    ),
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await prediction_service.predict_pneumonia(
                        session,
                        10,
                    )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "invalid_xray_image")

    async def test_get_predictions_returns_page_contract(self) -> None:
        session = AsyncMock()
        predictions = [make_prediction()]

        with (
            patch(
                "app.services.prediction_service.prediction_repository."
                "get_medical_record_by_id",
                new_callable=AsyncMock,
                return_value=object(),
            ),
            patch(
                "app.services.prediction_service.list_prediction_results",
                new_callable=AsyncMock,
                return_value=(predictions, 1),
            ) as list_prediction_results,
        ):
            result = await prediction_service.get_predictions(
                session,
                10,
                2,
                5,
            )

        self.assertEqual(result["page"], 2)
        self.assertEqual(result["size"], 5)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["predictions"][0]["id"], 1)
        list_prediction_results.assert_awaited_once_with(
            session,
            record_id=10,
            page=2,
            size=5,
        )

    async def test_get_predictions_rejects_missing_record(self) -> None:
        session = AsyncMock()
        with patch(
            "app.services.prediction_service.prediction_repository."
            "get_medical_record_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with self.assertRaises(HTTPException) as raised:
                await prediction_service.get_predictions(
                    session,
                    999,
                    1,
                    10,
                )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(
            raised.exception.detail,
            "medical_record_not_found",
        )

    def test_resolve_xray_image_path_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory(
            dir=Path.cwd(),
            prefix="prediction-test-",
        ) as temporary_directory:
            with (
                patch.object(
                    prediction_service,
                    "XRAY_MEDIA_ROOT",
                    Path(temporary_directory).resolve(),
                ),
                self.assertRaises(HTTPException) as raised,
            ):
                prediction_service.resolve_xray_image_path(
                    "/media/xray/../../secret.png"
                )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail, "xray_image_not_found")

    def test_router_access_detail_is_exported(self) -> None:
        self.assertEqual(
            prediction_service.PREDICTION_ACCESS_DENIED_DETAIL,
            "prediction_access_denied",
        )


if __name__ == "__main__":
    unittest.main()
