"""Password hashing and minimal JWT helpers used by the user API."""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return "pbkdf2_sha256$600000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
        return hmac.compare_digest(actual, base64.urlsafe_b64decode(expected))
    except (ValueError, TypeError):
        return False


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_token(user_id: int, expires_delta: timedelta) -> str:
    header = _b64encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64encode(json.dumps({"user_id": user_id, "exp": int((datetime.now(UTC) + expires_delta).timestamp())}, separators=(",", ":")).encode())
    signature = _b64encode(hmac.new(settings.JWT_SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def decode_token(token: str) -> int:
    try:
        header, payload, signature = token.split(".")
        expected = _b64encode(hmac.new(settings.JWT_SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        claims = json.loads(_b64decode(payload))
        if not isinstance(claims.get("user_id"), int) or claims["exp"] < datetime.now(UTC).timestamp():
            raise ValueError
        return claims["user_id"]
    except (ValueError, KeyError, json.JSONDecodeError):
        raise ValueError("Invalid token")
