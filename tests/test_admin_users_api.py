import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.main import app
from app.models.enums import Department, Gender, Role
from app.models.user import User


def _make_user(user_id: int, role: Role) -> User:
    return User(
        id=user_id,
        email=f"user{user_id}@example.com",
        hashed_password="hashed-password",
        name="테스트유저",
        department=Department.MEDICAL,
        gender=Gender.M,
        phone_number="01012345678",
        role=role,
        is_active=True,
    )


class AdminUsersApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.admin_user = _make_user(1, Role.ADMIN)
        self.db = AsyncMock()

        async def override_get_db():
            yield self.db

        self._override_get_db = override_get_db
        app.dependency_overrides[async_get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def _override_current_user(self, user: User) -> None:
        async def override_get_current_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = override_get_current_user

    def test_update_user_role_succeeds_for_admin(self) -> None:
        self._override_current_user(self.admin_user)
        target = _make_user(2, Role.PENDING)
        result = MagicMock()
        result.scalar_one_or_none.return_value = target
        self.db.execute.return_value = result

        response = self.client.patch(
            "/api/v1/users/2/role",
            json={"role": "STAFF"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "STAFF")
        self.db.commit.assert_awaited_once()

    def test_list_users_returns_paginated_results_for_admin(self) -> None:
        self._override_current_user(self.admin_user)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [
            _make_user(2, Role.STAFF),
            _make_user(3, Role.PENDING),
        ]
        total_result = MagicMock()
        total_result.scalar_one.return_value = 2
        self.db.execute.side_effect = [users_result, total_result]

        response = self.client.get("/api/v1/users?keyword=user&page=1&size=10")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 2)
        self.assertEqual(response.json()["page"], 1)
        self.assertEqual(response.json()["users"][0]["role"], "STAFF")
        self.assertEqual(self.db.execute.await_count, 2)

    def test_update_user_role_rejects_non_admin(self) -> None:
        self._override_current_user(_make_user(2, Role.STAFF))

        response = self.client.patch(
            "/api/v1/users/2/role",
            json={"role": "STAFF"},
        )

        self.assertEqual(response.status_code, 403)
        self.db.commit.assert_not_awaited()

    def test_update_user_role_requires_authentication(self) -> None:
        response = self.client.patch(
            "/api/v1/users/2/role",
            json={"role": "STAFF"},
        )

        self.assertEqual(response.status_code, 401)

    def test_update_user_role_rejects_unknown_role(self) -> None:
        self._override_current_user(self.admin_user)

        response = self.client.patch(
            "/api/v1/users/2/role",
            json={"role": "SUPERUSER"},
        )

        self.assertEqual(response.status_code, 422)
        self.db.commit.assert_not_awaited()

    def test_update_user_role_returns_404_when_user_missing(self) -> None:
        self._override_current_user(self.admin_user)
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result

        response = self.client.patch(
            "/api/v1/users/999/role",
            json={"role": "STAFF"},
        )

        self.assertEqual(response.status_code, 404)
        self.db.commit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
