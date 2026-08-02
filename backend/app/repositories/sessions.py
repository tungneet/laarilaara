"""Session repository (DynamoDB single-table).

Session item:
    PK = ``ACCOUNT#{accountId}``   SK = ``SESSION#{sessionId}``
    GSI1PK = ``SESSION#{sessionId}``  GSI1SK = ``SESSION``

Stores only the refresh token's hash, never the plaintext. ``familyId`` groups
a chain of rotated refresh tokens: each refresh rotates to a brand-new session
item with the same ``familyId`` and marks the old one ``consumed``. If a
``consumed`` token is ever presented again, it means an old token leaked and
was replayed — the whole family is revoked.

A refresh token has the wire format ``{sessionId}.{secret}``. The session id
prefix lets us find the item via GSI1 without knowing the account id; only the
secret's hash is compared against the stored hash.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.dynamodb import GSI1_NAME, get_table
from app.core.security import generate_opaque_token, sha256_hex


class RefreshTokenInvalidError(Exception):
    """Unknown, expired, revoked, or already-rotated-away refresh token."""


class SessionNotFoundError(Exception):
    """No session with this id exists for this account."""


def _account_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _session_sk(session_id: str) -> str:
    return f"SESSION#{session_id}"


def _put_session(
    account_id: str, session_id: str, family_id: str, refresh_secret: str
) -> None:
    settings = get_settings()
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(days=settings.auth.refresh_token_ttl_days)
    table.put_item(
        Item={
            "PK": _account_pk(account_id),
            "SK": _session_sk(session_id),
            "GSI1PK": f"SESSION#{session_id}",
            "GSI1SK": "SESSION",
            "entityType": "Session",
            "id": session_id,
            "accountId": account_id,
            "familyId": family_id,
            "refreshTokenHash": sha256_hex(refresh_secret),
            "revoked": False,
            "consumed": False,
            "createdAt": now.isoformat(),
            "expiresAt": expires_at.isoformat(),
            "ttl": int(expires_at.timestamp()),
        }
    )


def create_session(account_id: str) -> tuple[str, str]:
    """Create a new session and return (session_id, refresh_token).

    The refresh token is returned once, in plaintext, to the caller; only its
    hash is persisted.
    """
    session_id = uuid.uuid4().hex
    secret = generate_opaque_token()
    _put_session(account_id, session_id, family_id=session_id, refresh_secret=secret)
    return session_id, f"{session_id}.{secret}"


def _get_session_item(session_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression="GSI1PK = :pk AND GSI1SK = :sk",
        ExpressionAttributeValues={":pk": f"SESSION#{session_id}", ":sk": "SESSION"},
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def _revoke_family(account_id: str, family_id: str) -> None:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _account_pk(account_id),
            ":sk_prefix": "SESSION#",
        },
    )
    for item in resp.get("Items", []):
        if item.get("familyId") == family_id and not item.get("revoked"):
            table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET revoked = :true",
                ExpressionAttributeValues={":true": True},
            )


def rotate_session(refresh_token: str) -> tuple[str, str, str]:
    """Verify and rotate a refresh token.

    Returns (account_id, new_session_id, new_refresh_token). Raises
    ``RefreshTokenInvalidError`` for any failure, including reuse of an
    already-rotated-away token (which revokes the whole session family as a
    side effect).
    """
    session_id, _, secret = refresh_token.partition(".")
    if not session_id or not secret:
        raise RefreshTokenInvalidError("malformed_token")

    item = _get_session_item(session_id)
    if item is None:
        raise RefreshTokenInvalidError("not_found")
    if sha256_hex(secret) != item["refreshTokenHash"]:
        raise RefreshTokenInvalidError("hash_mismatch")

    account_id = item["accountId"]
    now = datetime.now(tz=timezone.utc)
    expires_at = datetime.fromisoformat(item["expiresAt"])

    if item.get("consumed"):
        # Reuse of a rotated-away token: treat as a compromised chain.
        _revoke_family(account_id, item["familyId"])
        raise RefreshTokenInvalidError("reused")
    if item.get("revoked") or now >= expires_at:
        raise RefreshTokenInvalidError("revoked_or_expired")

    try:
        table = get_table()
        table.update_item(
            Key={"PK": item["PK"], "SK": item["SK"]},
            UpdateExpression="SET #consumed = :true",
            ConditionExpression="#consumed = :false AND revoked = :false",
            ExpressionAttributeNames={"#consumed": "consumed"},
            ExpressionAttributeValues={":true": True, ":false": False},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RefreshTokenInvalidError("revoked_or_expired") from exc
        raise

    new_session_id = uuid.uuid4().hex
    new_secret = generate_opaque_token()
    _put_session(
        account_id, new_session_id, family_id=item["familyId"], refresh_secret=new_secret
    )
    return account_id, new_session_id, f"{new_session_id}.{new_secret}"


def revoke_session(account_id: str, session_id: str) -> None:
    table = get_table()
    try:
        table.update_item(
            Key={"PK": _account_pk(account_id), "SK": _session_sk(session_id)},
            UpdateExpression="SET revoked = :true",
            ConditionExpression="attribute_exists(PK)",
            ExpressionAttributeValues={":true": True},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise SessionNotFoundError(session_id) from exc
        raise


def list_sessions(account_id: str) -> list[dict]:
    """Return the account's non-revoked, non-rotated-away sessions."""
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _account_pk(account_id),
            ":sk_prefix": "SESSION#",
        },
    )
    return [
        item
        for item in resp.get("Items", [])
        if not item.get("revoked") and not item.get("consumed")
    ]


def revoke_all_sessions(account_id: str) -> None:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _account_pk(account_id),
            ":sk_prefix": "SESSION#",
        },
    )
    for item in resp.get("Items", []):
        if not item.get("revoked"):
            table.update_item(
                Key={"PK": item["PK"], "SK": item["SK"]},
                UpdateExpression="SET revoked = :true",
                ExpressionAttributeValues={":true": True},
            )

