import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.core.db.databases import async_get_db
from app.core.security import get_current_user
from app.main import app
from app.models.enums import Department, Gender, Role
from app.models.user import User


def _make_user() -> User:
    return User(
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


class AuthTokenFlowApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.user = _make_user()
        self.db = AsyncMock()
        self.db.add = MagicMock()

        async def override_get_db():
            yield self.db

        app.dependency_overrides[async_get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        app.dependency_overrides.clear()

    def test_login_issues_refresh_cookie_and_persists_token(self) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = self.user
        self.db.execute.return_value = result

        with (
            patch("app.apis.auth.verify_password", return_value=True),
            patch("app.apis.auth.create_access_token", return_value="access-token"),
            patch(
                "app.apis.auth.issue_refresh_token",
                new_callable=AsyncMock,
                return_value="refresh-token",
            ) as issue_refresh_token,
        ):
            response = self.client.post(
                "/api/v1/auth/login",
                json={"email": self.user.email, "password": "Password123!"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["access_token"], "access-token")
        self.assertIn("refresh_token=refresh-token", response.headers["set-cookie"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Path=/api/v1/auth", response.headers["set-cookie"])
        issue_refresh_token.assert_awaited_once_with(self.db, self.user.id)
        self.db.commit.assert_awaited_once()

    def test_signup_creates_pending_user_with_hashed_password(self) -> None:
        self.db.scalar.side_effect = [None, None]

        async def assign_user_id(user: User) -> None:
            user.id = 2

        self.db.refresh.side_effect = assign_user_id
        with patch("app.apis.auth.hash_password", return_value="hashed-new-password"):
            response = self.client.post(
                "/api/v1/auth/signup",
                json={
                    "email": "new-doctor@example.com",
                    "password": "Password123!",
                    "name": "새사용자",
                    "department": "MEDICAL",
                    "gender": "M",
                    "phone_number": "01022223333",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["department"], "MEDICAL")
        self.assertEqual(response.json()["gender"], "M")
        self.assertEqual(response.json()["role"], "PENDING")
        created_user = self.db.add.call_args.args[0]
        self.assertEqual(created_user.hashed_password, "hashed-new-password")
        self.assertEqual(created_user.role, Role.PENDING)
        self.db.commit.assert_awaited_once()

    def test_logout_requires_authentication_and_revokes_tokens(self) -> None:
        unauthenticated = self.client.post("/api/v1/auth/logout")
        self.assertEqual(unauthenticated.status_code, 401)

        async def override_current_user() -> User:
            return self.user

        app.dependency_overrides[get_current_user] = override_current_user
        with patch(
            "app.apis.auth.revoke_all_refresh_tokens", new_callable=AsyncMock
        ) as revoke_refresh_tokens:
            response = self.client.post("/api/v1/auth/logout")

        self.assertEqual(response.status_code, 200)
        revoke_refresh_tokens.assert_awaited_once_with(self.db, self.user.id)
        self.db.commit.assert_awaited_once()
        self.assertIn("refresh_token=\"\"", response.headers["set-cookie"])

    def test_refresh_rotates_refresh_cookie(self) -> None:
        with (
            patch(
                "app.apis.auth.rotate_refresh_token",
                new_callable=AsyncMock,
                return_value=(self.user, "replacement-token"),
            ) as rotate_refresh_token,
            patch("app.apis.auth.create_access_token", return_value="new-access-token"),
        ):
            response = self.client.post(
                "/api/v1/auth/refresh", headers={"Cookie": "refresh_token=current-token"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["access_token"], "new-access-token")
        self.assertIn("refresh_token=replacement-token", response.headers["set-cookie"])
        self.assertIn("Path=/api/v1/auth", response.headers["set-cookie"])
        rotate_refresh_token.assert_awaited_once_with(self.db, "current-token")


if __name__ == "__main__":
    unittest.main()
