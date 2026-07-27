import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.main import app
from app.models.enums import Department, Gender, Role
from app.models.user import User


class PredictionApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.user = User(
            id=1,
            email="staff@example.com",
            hashed_password="hashed-password",
            name="승인 사용자",
            department=Department.MEDICAL,
            gender=Gender.F,
            phone_number="01012345678",
            role=Role.STAFF,
            is_active=True,
        )
        self.session = AsyncMock()

        async def override_get_db():
            yield self.session

        async def override_get_current_user() -> User:
            return self.user

        app.dependency_overrides[async_get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def prediction_data(self, *, cached: bool = False) -> dict:
        return {
            "id": 101,
            "record_id": 10,
            "is_pneumonia": True,
            "confidence": 94.28,
            "heatmap_url": None,
            "ai_model": "simple-cnn-state-dict-v1",
            "created_at": datetime(2026, 7, 27, 10, 30),
            "cached": cached,
        }

    def test_predict_returns_new_prediction_contract(self) -> None:
        result = self.prediction_data()
        with patch(
            "app.apis.medical_records.prediction_service.predict_pneumonia",
            new_callable=AsyncMock,
            return_value=result,
        ) as predict:
            response = self.client.post(
                "/api/v1/medical-records/10/ai-predictions"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                **result,
                "created_at": "2026-07-27T10:30:00",
            },
        )
        predict.assert_awaited_once_with(
            session=self.session,
            record_id=10,
        )

    def test_predict_returns_cached_result_contract(self) -> None:
        result = self.prediction_data(cached=True)
        with patch(
            "app.apis.medical_records.prediction_service.predict_pneumonia",
            new_callable=AsyncMock,
            return_value=result,
        ):
            response = self.client.post(
                "/api/v1/medical-records/10/ai-predictions"
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["cached"])

    def test_list_predictions_returns_frontend_envelope(self) -> None:
        prediction = self.prediction_data()
        prediction.pop("cached")
        result = {
            "predictions": [prediction],
            "page": 2,
            "size": 5,
            "total": 6,
        }
        with patch(
            "app.apis.medical_records.prediction_service.get_predictions",
            new_callable=AsyncMock,
            return_value=result,
        ) as get_predictions:
            response = self.client.get(
                "/api/v1/medical-records/10/ai-predictions",
                params={"page": 2, "size": 5},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["page"], 2)
        self.assertEqual(response.json()["size"], 5)
        self.assertEqual(response.json()["total"], 6)
        self.assertEqual(len(response.json()["predictions"]), 1)
        get_predictions.assert_awaited_once_with(
            session=self.session,
            record_id=10,
            page=2,
            size=5,
        )

    def test_list_predictions_returns_empty_page(self) -> None:
        with patch(
            "app.apis.medical_records.prediction_service.get_predictions",
            new_callable=AsyncMock,
            return_value={
                "predictions": [],
                "page": 1,
                "size": 10,
                "total": 0,
            },
        ):
            response = self.client.get(
                "/api/v1/medical-records/10/ai-predictions"
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["predictions"], [])
        self.assertEqual(response.json()["total"], 0)

    def test_prediction_requires_authentication(self) -> None:
        del app.dependency_overrides[get_current_user]

        response = self.client.post(
            "/api/v1/medical-records/10/ai-predictions"
        )

        self.assertEqual(response.status_code, 401)

    def test_prediction_rejects_pending_user(self) -> None:
        self.user.role = Role.PENDING

        response = self.client.post(
            "/api/v1/medical-records/10/ai-predictions"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "prediction_access_denied")

    def test_list_rejects_invalid_pagination(self) -> None:
        response = self.client.get(
            "/api/v1/medical-records/10/ai-predictions",
            params={"page": 0, "size": 101},
        )

        self.assertEqual(response.status_code, 422)

    def test_prediction_rejects_invalid_record_id(self) -> None:
        response = self.client.post(
            "/api/v1/medical-records/0/ai-predictions"
        )

        self.assertEqual(response.status_code, 422)

    def test_predict_preserves_service_not_found_error(self) -> None:
        with patch(
            "app.apis.medical_records.prediction_service.predict_pneumonia",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=404,
                detail="medical_record_not_found",
            ),
        ):
            response = self.client.post(
                "/api/v1/medical-records/999/ai-predictions"
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "medical_record_not_found")

    def test_predict_preserves_model_unavailable_error(self) -> None:
        with patch(
            "app.apis.medical_records.prediction_service.predict_pneumonia",
            new_callable=AsyncMock,
            side_effect=HTTPException(
                status_code=503,
                detail="model_unavailable",
            ),
        ):
            response = self.client.post(
                "/api/v1/medical-records/10/ai-predictions"
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "model_unavailable")


if __name__ == "__main__":
    unittest.main()
