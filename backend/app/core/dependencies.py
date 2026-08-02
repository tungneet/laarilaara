"""FastAPI dependency for endpoints that require a bearer access token."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ApiError
from app.core.security import InvalidTokenError, decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHENTICATED_ERROR = ApiError(
    status=status.HTTP_401_UNAUTHORIZED,
    code="UNAUTHENTICATED",
    title="Missing or invalid access token",
)

_ADMIN_REQUIRED_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="ADMIN_REQUIRED",
    title="Admin role required",
)


@dataclass
class CurrentSession:
    account_id: str
    session_id: str
    tier: str
    role: str = "member"


def get_current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentSession:
    if credentials is None:
        raise _UNAUTHENTICATED_ERROR
    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise _UNAUTHENTICATED_ERROR from exc

    return CurrentSession(
        account_id=payload["sub"],
        session_id=payload["sid"],
        tier=payload.get("tier", "free"),
        role=payload.get("role", "member"),
    )


def get_current_admin_session(
    current: CurrentSession = Depends(get_current_session),
) -> CurrentSession:
    """Catalog §15: admin routes require a scoped ``admin`` role, not just
    any authenticated session. There is no self-serve way to obtain this
    role (see `app/domain/accounts.py::AccountRole`); non-admins get a
    generic 403 rather than a 404, since admin route existence is not a
    secret worth masking.
    """
    if current.role != "admin":
        raise _ADMIN_REQUIRED_ERROR
    return current
