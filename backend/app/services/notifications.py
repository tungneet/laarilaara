"""Outbound transactional email and SMS delivery.

Local/development stores codes in memory for the dev-only helper endpoint.
Staging/production sends email through Amazon SES v2 and SMS through Amazon
SNS, and never logs secret codes.
"""
from __future__ import annotations

import html
import re
import secrets
from functools import lru_cache

import boto3

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Local-development convenience only: the most recent code issued per
# email/phone, readable via the dev-only router (app/routers/dev.py).
# Populated exclusively inside the local/development branches below — never
# in staging/production.
_dev_last_codes: dict[str, dict] = {}

# E.164-ish phone number: leading + then 8-15 digits. Anything else is
# treated as an email address (the existing contact-verification flow passes
# either kind of value through the same functions).
_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def is_phone_number(value: str) -> bool:
    return bool(_PHONE_RE.match(value.strip()))


def peek_dev_code(email: str) -> dict | None:
    """Return the most recent locally-issued code entry for ``email``."""
    return _dev_last_codes.get(email.lower())


def generate_numeric_code(digits: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(digits))


@lru_cache
def get_ses_client():
    settings = get_settings()
    return boto3.client("sesv2", region_name=settings.aws_region)


@lru_cache
def get_sns_client():
    settings = get_settings()
    return boto3.client("sns", region_name=settings.aws_region)


def _send_email(email: str, subject: str, text_body: str, html_body: str) -> None:
    settings = get_settings()
    if settings.email.provider != "ses":
        raise RuntimeError(
            "Transactional email requires email.provider=ses outside local development"
        )

    get_ses_client().send_email(
        FromEmailAddress=settings.email.sender,
        Destination={"ToAddresses": [email]},
        Content={
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            }
        },
    )


def _send_sms(phone: str, message: str) -> None:
    """Send a transactional SMS via SNS. No sender-identity setup needed
    (unlike SES) — SNS can publish directly to any phone number, subject to
    the account's per-region SMS spending limit."""
    get_sns_client().publish(
        PhoneNumber=phone,
        Message=message,
        MessageAttributes={
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                # "Transactional" prioritizes delivery reliability over cost,
                # appropriate for one-time verification codes.
                "StringValue": "Transactional",
            }
        },
    )


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
        return

    if is_phone_number(email):
        _send_sms(
            email,
            f"Your LaariLaara verification code is {code}. It expires shortly.",
        )
        logger.info("verification SMS dispatched")
        return

    safe_code = html.escape(code)
    safe_challenge_id = html.escape(challenge_id)
    _send_email(
        email,
        "Your LaariLaara verification code",
        (
            "Your LaariLaara verification code is "
            f"{code}.\n\nChallenge ID: {challenge_id}\n\n"
            "This code expires shortly. If you did not request it, ignore this email."
        ),
        (
            "<h1>Verify your email</h1>"
            "<p>Use this code to continue with LaariLaara:</p>"
            f"<p style=\"font-size:28px;font-weight:700;letter-spacing:4px\">{safe_code}</p>"
            f"<p><strong>Challenge ID:</strong> {safe_challenge_id}</p>"
            "<p>This code expires shortly. If you did not request it, ignore this email.</p>"
        ),
    )
    logger.info("verification email dispatched")


def send_manager_invitation(email: str, token: str, invitation_id: str) -> None:
    settings = get_settings()
    if settings.environment in ("local", "development"):
        logger.info(
            "manager invitation for %s: token %s (invitation %s)",
            email,
            token,
            invitation_id,
        )
        return

    safe_token = html.escape(token)
    safe_invitation_id = html.escape(invitation_id)
    _send_email(
        email,
        "You have been invited to manage a LaariLaara profile",
        (
            "You have been invited to help manage a LaariLaara profile.\n\n"
            f"Invitation ID: {invitation_id}\nToken: {token}"
        ),
        (
            "<h1>Profile manager invitation</h1>"
            "<p>You have been invited to help manage a LaariLaara profile.</p>"
            f"<p><strong>Invitation ID:</strong> {safe_invitation_id}</p>"
            f"<p><strong>Token:</strong> {safe_token}</p>"
        ),
    )
    logger.info("manager invitation dispatched")
