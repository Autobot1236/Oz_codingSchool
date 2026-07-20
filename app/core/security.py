import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.auth_config import auth_settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: int) -> tuple[str, int]:
    now = datetime.now(UTC)
    expires_in = auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = jwt.encode(
        {"user_id": user_id, "iat": now, "exp": now + timedelta(seconds=expires_in)},
        auth_settings.JWT_SECRET_KEY,
        algorithm=auth_settings.JWT_ALGORITHM,
    )
    return token, expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        auth_settings.JWT_SECRET_KEY,
        algorithms=[auth_settings.JWT_ALGORITHM],
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
