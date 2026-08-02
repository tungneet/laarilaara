"""Local-development-only helpers.

This router is mounted ONLY when ``settings.environment`` is ``local`` or
``development`` (see ``create_app``). It must never ship enabled to staging
or production: it exposes verification codes, which would otherwise arrive
by email, so developers can complete the signup flow without a mail sender.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.errors import ApiError
from app.services import notifications as notifications_service

router = APIRouter(prefix="/__dev__", tags=["dev"])

_NO_CODE_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="DEV_CODE_NOT_FOUND",
    title="No code has been issued for that email since the server started",
)


@router.get("/verification-code")
async def get_verification_code(email: str = Query(..., min_length=3)) -> dict:
    """The most recent verification code + challenge id issued to ``email``."""
    entry = notifications_service.peek_dev_code(email)
    if entry is None:
        raise _NO_CODE_ERROR
    return entry
