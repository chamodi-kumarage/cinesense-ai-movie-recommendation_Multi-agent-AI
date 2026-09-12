import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet
import jwt

from .config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """
    Hash passwords with bcrypt directly.

    Using bcrypt directly avoids the passlib/bcrypt compatibility warning
    produced by newer bcrypt releases on Python 3.14.
    """
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        # Existing passlib-generated bcrypt hashes use the same standard
        # $2b$ bcrypt format, so they remain compatible with checkpw().
        if hashed.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed.encode("utf-8"),
            )

        # Backward-compatible PBKDF2 fallback from an earlier CineSense build.
        if hashed.startswith("$pbkdf2$"):
            salt = hashlib.sha256(
                (settings.secret_key + ":pwd").encode()
            ).digest()[:16]
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                salt,
                240000,
            )
            expected = (
                "$pbkdf2$"
                + base64.urlsafe_b64encode(derived).decode()
            )
            return hashlib.compare_digest(expected, hashed)
    except Exception:
        return False

    return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(
            (
                now
                + timedelta(minutes=settings.access_token_minutes)
            ).timestamp()
        ),
    }
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> int | None:
    try:
        data = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return int(data["sub"])
    except Exception:
        return None


def _fernet() -> Fernet:
    digest = hashlib.sha256(
        settings.secret_key.encode()
    ).digest()
    return Fernet(
        base64.urlsafe_b64encode(digest)
    )


def encrypt_text(text: str) -> str:
    if not text:
        return ""
    return _fernet().encrypt(
        text.encode()
    ).decode()


def decrypt_text(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(
            token.encode()
        ).decode()
    except Exception:
        return ""
