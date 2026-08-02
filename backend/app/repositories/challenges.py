"""Verification challenge repository (DynamoDB single-table).

Challenge item:
    PK = ``ACCOUNT#{accountId}``   SK = ``CHALLENGE#{challengeId}``
    GSI1PK = ``CHALLENGE#{challengeId}``  GSI1SK = ``CHALLENGE``

The GSI lets ``POST /v1/auth/challenges/{challengeId}/verify`` look a challenge
up by id alone (the caller does not know their own accountId at that point).
The challengeId itself is only ever delivered out-of-band (the verification
email/SMS), never in a register-endpoint API response, so this lookup does not
enable enumeration.

Stores only the hashed code, an expiry, an attempt counter, and a consumed
flag. A DynamoDB TTL attribute (``ttl``) lets expired challenges be reaped
automatically.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.dynamodb import GSI1_NAME, get_table
from app.core.security import hash_challenge_code


class ChallengeNotFoundError(Exception):
    pass


class ChallengeInvalidError(Exception):
    """Expired, consumed, over attempt limit, or wrong code — all generic."""


class Challenge:
    def __init__(
        self, challenge_id: str, account_id: str, subject_id: str | None = None
    ) -> None:
        self.id = challenge_id
        self.account_id = account_id
        self.subject_id = subject_id


def _challenge_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _challenge_sk(challenge_id: str) -> str:
    return f"CHALLENGE#{challenge_id}"


def create_email_verification_challenge(account_id: str, code: str) -> Challenge:
    return _create_challenge(account_id, code, purpose="email_verification")


def create_password_reset_challenge(account_id: str, code: str) -> Challenge:
    return _create_challenge(account_id, code, purpose="password_reset")


def create_contact_verification_challenge(
    account_id: str, code: str, contact_id: str
) -> Challenge:
    return _create_challenge(
        account_id, code, purpose="contact_verification", subject_id=contact_id
    )


def _create_challenge(
    account_id: str, code: str, purpose: str, subject_id: str | None = None
) -> Challenge:
    settings = get_settings()
    table = get_table()
    challenge_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(minutes=settings.auth.challenge_ttl_minutes)

    table.put_item(
        Item={
            "PK": _challenge_pk(account_id),
            "SK": _challenge_sk(challenge_id),
            "GSI1PK": f"CHALLENGE#{challenge_id}",
            "GSI1SK": "CHALLENGE",
            "entityType": "Challenge",
            "id": challenge_id,
            "accountId": account_id,
            "purpose": purpose,
            "subjectId": subject_id,
            "codeHash": hash_challenge_code(challenge_id, code),
            "attempts": 0,
            "consumed": False,
            "createdAt": now.isoformat(),
            "expiresAt": expires_at.isoformat(),
            "ttl": int(expires_at.timestamp()),
        }
    )
    return Challenge(challenge_id, account_id, subject_id)


def _get_challenge_item(challenge_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression="GSI1PK = :pk AND GSI1SK = :sk",
        ExpressionAttributeValues={
            ":pk": f"CHALLENGE#{challenge_id}",
            ":sk": "CHALLENGE",
        },
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def verify_and_consume(
    challenge_id: str, code: str, expected_purpose: str
) -> tuple[str, str | None]:
    """Verify a code against a challenge and consume it atomically.

    Returns ``(account_id, subject_id)`` on success — ``subject_id`` is
    ``None`` unless the challenge was created with one (e.g. a contact id for
    contact-verification challenges). Raises ``ChallengeNotFoundError`` or
    ``ChallengeInvalidError`` on any failure (including a purpose mismatch,
    e.g. presenting an email-verification code to the password-reset
    endpoint); callers should return the same generic error response for all
    of these, per the API catalog's "generic failures" requirement.
    """
    settings = get_settings()
    table = get_table()
    item = _get_challenge_item(challenge_id)
    if item is None:
        raise ChallengeNotFoundError(challenge_id)
    if item["purpose"] != expected_purpose:
        raise ChallengeInvalidError("wrong_purpose")

    account_id = item["accountId"]
    now = datetime.now(tz=timezone.utc)
    expires_at = datetime.fromisoformat(item["expiresAt"])
    if item["consumed"] or now >= expires_at:
        raise ChallengeInvalidError("expired_or_consumed")
    if item["attempts"] >= settings.auth.max_challenge_attempts:
        raise ChallengeInvalidError("too_many_attempts")

    # Atomically record the attempt, bounded by the same conditions checked
    # above, so concurrent verify calls cannot exceed the attempt limit or
    # race past consumption.
    try:
        table.update_item(
            Key={"PK": _challenge_pk(account_id), "SK": _challenge_sk(challenge_id)},
            UpdateExpression="SET attempts = attempts + :one",
            ConditionExpression="#consumed = :false AND attempts < :max_attempts",
            ExpressionAttributeNames={"#consumed": "consumed"},
            ExpressionAttributeValues={
                ":one": 1,
                ":false": False,
                ":max_attempts": settings.auth.max_challenge_attempts,
            },
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ChallengeInvalidError("too_many_attempts") from exc
        raise

    if hash_challenge_code(challenge_id, code) != item["codeHash"]:
        raise ChallengeInvalidError("wrong_code")

    try:
        table.update_item(
            Key={"PK": _challenge_pk(account_id), "SK": _challenge_sk(challenge_id)},
            UpdateExpression="SET #consumed = :true",
            ConditionExpression="#consumed = :false",
            ExpressionAttributeNames={"#consumed": "consumed"},
            ExpressionAttributeValues={":true": True, ":false": False},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ChallengeInvalidError("expired_or_consumed") from exc
        raise

    return account_id, item.get("subjectId")

