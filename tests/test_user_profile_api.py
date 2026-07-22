import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.main import app
from app.models.enums import Department, Gender, Role
from app.models.user import User


class UserProfileApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.user = User(
            id=1,
            email="doctor@example.com",
            hashed_password="hashed-password",
            name="홍길동",
            department=Department.MEDICAL,
            gender=Gender.M,
            phone_number="01012345678",
            role=Role.STAFF,
            is_active=True,
        )
        self.db = AsyncMock()

        async def override_get_db():
            yield self.db

        async def override_get_current_user() -> User:
            return self.user

        app.dependency_overrides[async_get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_get_my_profile_returns_only_allowed_fields(self) -> None:
        response = self.client.get("/api/v1/users/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "name": "홍길동",
                "email": "doctor@example.com",
                "department": "MEDICAL",
                "gender": "M",
                "phone_number": "01012345678",
                "role": "STAFF",
            },
        )
        self.assertNotIn("hashed_password", response.json())

    def test_get_my_profile_requires_authentication(self) -> None:
        del app.dependency_overrides[get_current_user]

        response = self.client.get("/api/v1/users/me")

        self.assertEqual(response.status_code, 401)

    def test_patch_my_profile_updates_only_department(self) -> None:
        response = self.client.patch(
            "/api/v1/users/me",
            json={"department": "RESEARCH"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["department"], "RESEARCH")
        self.assertEqual(response.json()["phone_number"], "01012345678")
        self.db.execute.assert_not_awaited()
        self.db.commit.assert_awaited_once()

    def test_patch_my_profile_updates_unique_phone_number(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        response = self.client.patch(
            "/api/v1/users/me",
            json={"phone_number": "01098765432"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["phone_number"], "01098765432")
        self.db.execute.assert_awaited_once()
        self.db.commit.assert_awaited_once()

    def test_patch_my_profile_rejects_duplicate_phone_number(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = 2
        self.db.execute.return_value = result

        response = self.client.patch(
            "/api/v1/users/me",
            json={"phone_number": "01099998888"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "이미 등록된 휴대폰 번호입니다.")
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rejects_empty_payload(self) -> None:
        response = self.client.patch("/api/v1/users/me", json={})

        self.assertEqual(response.status_code, 400)
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rejects_unsupported_field(self) -> None:
        response = self.client.patch(
            "/api/v1/users/me",
            json={"name": "수정할 수 없는 이름"},
        )

        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rejects_invalid_department(self) -> None:
        response = self.client.patch(
            "/api/v1/users/me",
            json={"department": "SALES"},
        )

        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rejects_non_contract_department_alias(self) -> None:
        response = self.client.patch(
            "/api/v1/users/me",
            json={"department": "DEVELOPMENT"},
        )

        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rejects_invalid_phone_number(self) -> None:
        response = self.client.patch(
            "/api/v1/users/me",
            json={"phone_number": "010-1234-5678"},
        )

        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rejects_explicit_null(self) -> None:
        response = self.client.patch(
            "/api/v1/users/me",
            json={"department": None},
        )

        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_awaited()

    def test_patch_my_profile_rolls_back_unique_constraint_conflict(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result
        self.db.commit.side_effect = IntegrityError(
            "UPDATE users",
            {},
            Exception("duplicate phone number"),
        )

        response = self.client.patch(
            "/api/v1/users/me",
            json={"phone_number": "01099998888"},
        )

        self.assertEqual(response.status_code, 409)
        self.db.rollback.assert_awaited_once()

    def test_delete_my_account_revokes_tokens_and_deletes_user(self) -> None:
        with patch(
            "app.apis.users.revoke_all_refresh_tokens", new_callable=AsyncMock
        ) as revoke_refresh_tokens:
            response = self.client.delete("/api/v1/users/me")

        self.assertEqual(response.status_code, 204)
        revoke_refresh_tokens.assert_awaited_once_with(self.db, self.user.id)
        self.db.delete.assert_awaited_once_with(self.user)
        self.db.commit.assert_awaited_once()

    def test_change_password_revokes_refresh_tokens(self) -> None:
        with (
            patch("app.apis.users.verify_password", side_effect=[True, False]),
            patch("app.apis.users.hash_password", return_value="new-hashed-password"),
            patch(
                "app.apis.users.revoke_all_refresh_tokens", new_callable=AsyncMock
            ) as revoke_refresh_tokens,
        ):
            response = self.client.patch(
                "/api/v1/users/me/password",
                json={
                    "current_password": "Password123!",
                    "new_password": "NewPassword123!",
                },
            )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.user.hashed_password, "new-hashed-password")
        revoke_refresh_tokens.assert_awaited_once_with(self.db, self.user.id)
        self.db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
