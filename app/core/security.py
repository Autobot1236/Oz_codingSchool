import base64
import os

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


SCRYPT_LENGTH = 32
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def _derive_password(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=SCRYPT_LENGTH,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return kdf.derive(password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Scrypt로 비밀번호를 해시하여 저장 가능한 문자열로 반환한다."""
    salt = os.urandom(16)
    derived_key = _derive_password(password, salt)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_key = base64.urlsafe_b64encode(derived_key).decode("ascii")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${encoded_salt}${encoded_key}"
