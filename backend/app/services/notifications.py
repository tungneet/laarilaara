"""Outbound notification seam (development stub).

Real delivery (email/SMS via SES or a provider) is deferred and will run in an
async worker. For now this logs the verification code so local development can
complete the flow. It must NEVER log codes outside local/development.
"""
from __future__ import annotations

import secrets

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Local-development convenience only: the most recent code issued per email,
# readable via the dev-only router (app/routers/dev.py). Populated exclusively
# inside the local/development branches below — never in staging/production.
_dev_last_codes: dict[str, dict] = {}


def peek_dev_code(email: str) -> dict | None:
    """Return the most recent locally-issued code entry for ``email``."""
    return _dev_last_codes.get(email.lower())


def generate_numeric_code(digits: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(digits))


def send_verification_code(email: str, code: str, challenge_id: str) -> None:
    settings = get_settings()
    if settings.environment in ("local", "development"):
        logger.info(
            "verification code for %s: %s (challenge %s)", email, code, challenge_id
        )
        _dev_last_codes[email.lower()] = {
            "email": email,
            "code": code,
            "challenge_id": challenge_id,
        }
    else:
        # Production path (SES/provider) is implemented in the notification
        # worker; never emit the code or challenge id to logs here.
        logger.info("verification code dispatched", extra={"extra_fields": {}})


def send_manager_invitation(email: str, token: str, invitation_id: str) -> None:
    settings = get_settings()
    if settings.environment in ("local", "development"):
        logger.info(
            "manager invitation for %s: token %s (invitation %s)",
            email,
            token,
            invitation_id,
        )
    else:
        # Production path (SES/provider) is implemented in the notification
        # worker; never emit the token or invitation id to logs here.
        logger.info("manager invitation dispatched", extra={"extra_fields": {}})
