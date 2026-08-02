"""Password hashing, token generation, and JWT access tokens.

- Passwords use ``hashlib.scrypt`` (standard library, memory-hard KDF) with a
  per-password random salt. The stored value encodes all parameters so
  verification is self-contained.
- Emails are normalized and hashed to build a deterministic DynamoDB lookup key,
  so we can enforce uniqueness and look accounts up without indexing plaintext.
- Refresh tokens are high-entropy opaque strings; only their SHA-256 hash is
  stored, so a DynamoDB read cannot yield a usable token.
- Access tokens are short-lived signed JWTs (HS256) so most requests can
  authenticate without a DynamoDB read; authorization/state checks still hit
  the data store.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from base64 import b64decode, b64encode
from typing import Any

import jwt

from app.core.config import get_settings

# scrypt cost parameters. n must be a power of two; these are a reasonable
# interactive-login default that stays well within a Lambda's CPU/time budget.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_DKLEN = 32
_JWT_ALGORITHM = "HS256"


class InvalidTokenError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_lookup_hash(email: str) -> str:
    """Deterministic hash of a normalized email for use as a lookup key."""
    normalized = normalize_email(email)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_opaque_token() -> str:
    """High-entropy, URL-safe token for refresh tokens."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
    )
    return "$".join(
        [
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            b64encode(salt).decode("ascii"),
            b64encode(derived).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n_s, r_s, p_s, salt_b64, hash_b64 = encoded.split("$")
        if scheme != "scrypt":
            return False
        salt = b64decode(salt_b64)
        expected = b64decode(hash_b64)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n_s),
            r=int(r_s),
            p=int(p_s),
            dklen=len(expected),
        )
        return hmac.compare_digest(derived, expected)
    except (ValueError, TypeError):
        return False


def hash_challenge_code(challenge_id: str, code: str) -> str:
    """Hash a short verification code, salted by its challenge id.

    Codes are low-entropy but short-lived and attempt-limited; the challenge id
    salt prevents cross-challenge precomputation.
    """
    return hashlib.sha256(f"{challenge_id}:{code}".encode("utf-8")).hexdigest()


def verify_challenge_code(challenge_id: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_challenge_code(challenge_id, code), code_hash)


def create_access_token(
    account_id: str, session_id: str, tier: str, role: str = "member"
) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    settings = get_settings()
    ttl_seconds = settings.auth.access_token_ttl_minutes * 60
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": account_id,
        "sid": session_id,
        "tier": tier,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + ttl_seconds,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)
    return token, ttl_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


_REALTIME_TOKEN_TTL_SECONDS = 60  # catalog §9: "short-lived connection token"


def create_realtime_token(account_id: str, profile_id: str) -> tuple[str, int]:
    """Short-lived, single-purpose token for the WebSocket `$connect` route
    (catalog §9 `POST /v1/realtime-tokens`). Kept separate from access tokens
    (``type=realtime`` instead of ``access``, much shorter TTL, carries a
    profile id) so it can never be mistaken for or reused as a bearer access
    token by `get_current_session`.
    """
    settings = get_settings()
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": account_id,
        "pid": profile_id,
        "type": "realtime",
        "iat": now,
        "exp": now + _REALTIME_TOKEN_TTL_SECONDS,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)
    return token, _REALTIME_TOKEN_TTL_SECONDS


def decode_realtime_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if payload.get("type") != "realtime":
        raise InvalidTokenError("not a realtime token")
    return payload
