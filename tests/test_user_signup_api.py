import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select

from app.core.db.databases import async_get_db
from app.core.passwords import verify_password
from app.models.enums import Department, Gender, Role
from app.models.user import User


SIGNUP_PAYLOAD = {
    "email": "Doctor@Example.com",
    "password": "Secure!234",
    "name": "홍길동",
    "department": "MEDICAL",
    "gender": "M",
    "phoneNumber": "01012345678",
}


async def _get_user(test_app: FastAPI, email: str) -> User | None:
    dependency = test_app.dependency_overrides[async_get_db]
    async for session in dependency():
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    return None


@pytest.mark.asyncio
async def test_signup_creates_pending_user_with_hashed_password(
    client: AsyncClient,
    test_app: FastAPI,
) -> None:
    response = await client.post("/api/v1/users", json=SIGNUP_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "success": True,
        "data": {
            "id": 1,
            "email": "doctor@example.com",
            "name": "홍길동",
            "department": "MEDICAL",
            "gender": "M",
            "phoneNumber": "01012345678",
            "role": "PENDING",
            "active": True,
            "createdAt": body["data"]["createdAt"],
        },
        "message": "회원가입이 완료되었습니다.",
    }
    assert body["data"]["createdAt"].endswith("Z")

    user = await _get_user(test_app, "doctor@example.com")
    assert user is not None
    assert user.role is Role.PENDING
    assert user.department is Department.MEDICAL
    assert user.gender is Gender.M
    assert user.hashed_password != SIGNUP_PAYLOAD["password"]
    assert verify_password(SIGNUP_PAYLOAD["password"], user.hashed_password)


@pytest.mark.asyncio
async def test_signup_accepts_development_alias(client: AsyncClient) -> None:
    payload = {
        **SIGNUP_PAYLOAD,
        "email": "developer@example.com",
        "department": "DEVELOPMENT",
        "phoneNumber": "01011112222",
    }

    response = await client.post("/api/v1/users", json=payload)

    assert response.status_code == 201
    assert response.json()["data"]["department"] == "DEV"


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_email(client: AsyncClient) -> None:
    first = await client.post("/api/v1/users", json=SIGNUP_PAYLOAD)
    duplicate = await client.post(
        "/api/v1/users",
        json={**SIGNUP_PAYLOAD, "phoneNumber": "01099998888"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_signup_rejects_duplicate_phone_number(client: AsyncClient) -> None:
    first = await client.post("/api/v1/users", json=SIGNUP_PAYLOAD)
    duplicate = await client.post(
        "/api/v1/users",
        json={**SIGNUP_PAYLOAD, "email": "another@example.com"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "PHONE_NUMBER_ALREADY_EXISTS"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "invalid-email"),
        ("password", "onlylowercase!"),
        ("name", "김"),
        ("phoneNumber", "010-1234-5678"),
    ],
)
async def test_signup_rejects_invalid_input(
    client: AsyncClient,
    field: str,
    value: str,
) -> None:
    response = await client.post(
        "/api/v1/users",
        json={**SIGNUP_PAYLOAD, field: value},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_signup_rejects_role_escalation(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={**SIGNUP_PAYLOAD, "role": "ADMIN"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_signup_is_exposed_in_openapi(test_app: FastAPI) -> None:
    operation = test_app.openapi()["paths"]["/api/v1/users"]["post"]
    assert operation["summary"] == "회원가입"
