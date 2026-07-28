import tempfile
import unittest
from datetime import datetime
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.main import app
from app.models.enums import Department, Gender, Role
from app.models.medical_record import MedicalRecord
from app.models.patient import Patient
from app.models.user import User
from app.schemas.medical_record import MedicalRecordCreateResponse
from app.schemas.patient import PatientResponse, PatientUpdateRequest
from app.services import medical_record_service, patient_service

NOW = datetime(2026, 7, 23, 10, 30, 0)


def make_user(department: Department = Department.MEDICAL) -> User:
    return User(
        id=1,
        email="staff@example.com",
        hashed_password="hashed-password",
        name="테스트사용자",
        department=department,
        gender=Gender.M,
        phone_number="01011112222",
        role=Role.PENDING,
        is_active=True,
    )


def make_patient() -> Patient:
    return Patient(
        id=3,
        name="김환자",
        age=42,
        gender=Gender.F,
        phone="01012345678",
        created_at=NOW,
        updated_at=None,
    )


class PatientMedicalRecordApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.session = AsyncMock()
        self.current_user = make_user()

        async def override_get_db():
            yield self.session

        async def override_current_user() -> User:
            return self.current_user

        app.dependency_overrides[async_get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_patch_patient_uses_patient_id_and_snake_case_body(self) -> None:
        response_model = PatientResponse(
            id=3,
            name="김새이름",
            age=42,
            gender=Gender.F,
            phone_number="01098765432",
            created_at=NOW,
            updated_at=NOW,
        )
        with patch(
            "app.services.patient_service.update_patient",
            new_callable=AsyncMock,
            return_value=response_model,
        ) as update_patient:
            response = self.client.patch(
                "/api/v1/patients/3",
                json={
                    "name": "김새이름",
                    "phone_number": "01098765432",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["phone_number"], "01098765432")
        update_patient.assert_awaited_once()
        self.assertEqual(update_patient.await_args.kwargs["patient_id"], 3)

    def test_patch_patient_rejects_empty_body(self) -> None:
        response = self.client.patch("/api/v1/patients/3", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "update_fields_required")

    def test_patch_patient_rejects_null(self) -> None:
        response = self.client.patch(
            "/api/v1/patients/3",
            json={"name": None},
        )

        self.assertEqual(response.status_code, 422)

    def test_post_medical_record_uses_nested_patient_path(self) -> None:
        response_model = MedicalRecordCreateResponse(
            id=10,
            patient_id=3,
            chart_number="C-2026-0001",
            symptoms="기침과 발열",
            xray_image_url="/media/xray/test.png",
            shooting_datetime=NOW,
            created_at=NOW,
        )
        with patch(
            "app.services.medical_record_service.create_medical_record",
            new_callable=AsyncMock,
            return_value=response_model,
        ) as create_medical_record:
            response = self.client.post(
                "/api/v1/patients/3/medical-records",
                data={
                    "chart_number": "C-2026-0001",
                    "symptoms": "기침과 발열",
                },
                files={
                    "xray_image": (
                        "xray.png",
                        b"\x89PNG\r\n\x1a\nsynthetic",
                        "image/png",
                    )
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["patient_id"], 3)
        create_medical_record.assert_awaited_once()
        self.assertEqual(
            create_medical_record.await_args.kwargs["patient_id"],
            3,
        )

    def test_post_medical_record_requires_xray_image(self) -> None:
        response = self.client.post(
            "/api/v1/patients/3/medical-records",
            data={
                "chart_number": "C-2026-0001",
                "symptoms": "기침과 발열",
            },
        )

        self.assertEqual(response.status_code, 422)


class PatientServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_update_patient_rejects_empty_payload(self) -> None:
        session = AsyncMock()
        with self.assertRaises(HTTPException) as raised:
            await patient_service.update_patient(
                session=session,
                patient_id=3,
                payload=PatientUpdateRequest(),
                current_user=make_user(),
            )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "update_fields_required")
        session.commit.assert_not_awaited()

    async def test_update_patient_rejects_non_medical_department(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            await patient_service.update_patient(
                session=AsyncMock(),
                patient_id=3,
                payload=PatientUpdateRequest(name="새이름"),
                current_user=make_user(Department.DEV),
            )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(
            raised.exception.detail,
            "medical_department_required",
        )

    async def test_update_patient_commits_partial_changes(self) -> None:
        session = AsyncMock()
        patient = make_patient()
        with (
            patch(
                "app.services.patient_service.patient_repository.get_patient_by_id",
                new_callable=AsyncMock,
                return_value=patient,
            ),
            patch(
                "app.services.patient_service.patient_repository.get_patient_by_phone_number",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            response = await patient_service.update_patient(
                session=session,
                patient_id=3,
                payload=PatientUpdateRequest(
                    name="김새이름",
                    phone_number="01098765432",
                ),
                current_user=make_user(),
            )

        self.assertEqual(response.name, "김새이름")
        self.assertEqual(response.phone_number, "01098765432")
        session.commit.assert_awaited_once()
        session.refresh.assert_awaited_once_with(patient)


class MedicalRecordServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_validate_xray_rejects_mime_signature_mismatch(self) -> None:
        upload = UploadFile(
            filename="fake.png",
            file=BytesIO(b"not-a-real-png"),
            headers=Headers({"content-type": "image/png"}),
        )

        with self.assertRaises(HTTPException) as raised:
            await medical_record_service.validate_xray_image(upload)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.detail, "invalid_xray_image")

    async def test_create_medical_record_saves_png_and_commits(self) -> None:
        session = AsyncMock()
        patient = make_patient()
        upload = UploadFile(
            filename="original-name.png",
            file=BytesIO(b"\x89PNG\r\n\x1a\nsynthetic-xray"),
            headers=Headers({"content-type": "image/png"}),
        )

        def assign_medical_record_id(
            _session,
            medical_record: MedicalRecord,
        ) -> None:
            medical_record.id = 10
            medical_record.created_at = NOW

        def assign_xray_image_id(_session, xray_image) -> None:
            xray_image.id = 20
            xray_image.created_at = NOW

        with (
            tempfile.TemporaryDirectory() as temporary_directory,
            patch.object(
                medical_record_service,
                "XRAY_MEDIA_ROOT",
                Path(temporary_directory),
            ),
            patch(
                "app.services.medical_record_service.patient_repository.get_patient_by_id",
                new_callable=AsyncMock,
                return_value=patient,
            ),
            patch.object(
                medical_record_service.medical_record_repository,
                "get_medical_record_by_chart_number",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.medical_record_service.medical_record_repository.add_medical_record",
                side_effect=assign_medical_record_id,
            ),
            patch(
                "app.services.medical_record_service.medical_record_repository.add_xray_image",
                side_effect=assign_xray_image_id,
            ),
        ):
            response = await medical_record_service.create_medical_record(
                session=session,
                patient_id=3,
                chart_number=" C-2026-0001 ",
                symptoms=" 기침과 발열 ",
                xray_image=upload,
                current_user=make_user(),
            )
            saved_files = list(Path(temporary_directory).glob("*.png"))

        self.assertEqual(response.id, 10)
        self.assertEqual(response.patient_id, 3)
        self.assertEqual(response.chart_number, "C-2026-0001")
        self.assertEqual(response.symptoms, "기침과 발열")
        self.assertEqual(len(saved_files), 1)
        self.assertNotEqual(saved_files[0].name, "original-name.png")
        session.commit.assert_awaited_once()

    async def test_create_medical_record_rejects_duplicate_chart_number(
        self,
    ) -> None:
        duplicate_record = MagicMock(spec=MedicalRecord)
        with (
            patch(
                "app.services.medical_record_service.patient_repository.get_patient_by_id",
                new_callable=AsyncMock,
                return_value=make_patient(),
            ),
            patch.object(
                medical_record_service.medical_record_repository,
                "get_medical_record_by_chart_number",
                new_callable=AsyncMock,
                return_value=duplicate_record,
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await medical_record_service.create_medical_record(
                    session=AsyncMock(),
                    patient_id=3,
                    chart_number="C-2026-0001",
                    symptoms="기침",
                    xray_image=MagicMock(spec=UploadFile),
                    current_user=make_user(),
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(
            raised.exception.detail,
            "chart_number_already_exists",
        )


if __name__ == "__main__":
    unittest.main()
