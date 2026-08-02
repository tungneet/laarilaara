"""Profile manager invitation repository (DynamoDB single-table).

Invitation item:  PK = ``PROFILE#{profileId}``   SK = ``INVITATION#{id}``

The invitation token is a high-entropy opaque secret delivered only via the
notification side-channel (never returned in the invite API response); only
its SHA-256 hash is stored, and accept looks the invitation up via GSI1 on
that hash (mirrors the pattern used for refresh-token sessions).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import GSI1_NAME, get_table
from app.core.security import generate_opaque_token, sha256_hex

INVITATION_TTL_HOURS = 72


class InvitationNotFoundError(Exception):
    pass


class InvitationNotPendingError(Exception):
    """Invitation already accepted/revoked, or has expired."""


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _invitation_sk(invitation_id: str) -> str:
    return f"INVITATION#{invitation_id}"


def create_invitation(
    profile_id: str,
    invited_by_account_id: str,
    invited_email: str,
    role: str,
    permissions: list[str],
) -> tuple[dict, str]:
    """Create a pending invitation and return (item, plaintext_token)."""
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(hours=INVITATION_TTL_HOURS)
    invitation_id = uuid.uuid4().hex
    token = generate_opaque_token()
    item = {
        "PK": _profile_pk(profile_id),
        "SK": _invitation_sk(invitation_id),
        "GSI1PK": f"INVITATIONTOKEN#{sha256_hex(token)}",
        "GSI1SK": "INVITATION",
        "entityType": "ProfileManagerInvitation",
        "id": invitation_id,
        "profileId": profile_id,
        "invitedByAccountId": invited_by_account_id,
        "invitedEmail": invited_email,
        "role": role,
        "permissions": permissions,
        "status": "pending",
        "createdAt": now.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "acceptedAt": None,
        "acceptedByAccountId": None,
    }
    table.put_item(Item=item)
    return item, token


def get_invitation_by_token(token: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression="GSI1PK = :pk AND GSI1SK = :sk",
        ExpressionAttributeValues={
            ":pk": f"INVITATIONTOKEN#{sha256_hex(token)}",
            ":sk": "INVITATION",
        },
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def list_invitations(profile_id: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _profile_pk(profile_id),
            ":sk_prefix": "INVITATION#",
        },
    )
    return resp.get("Items", [])


def mark_accepted(profile_id: str, invitation_id: str, accepted_by_account_id: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    try:
        resp = table.update_item(
            Key={"PK": _profile_pk(profile_id), "SK": _invitation_sk(invitation_id)},
            UpdateExpression=(
                "SET #status = :accepted, acceptedAt = :now, "
                "acceptedByAccountId = :accountId"
            ),
            ConditionExpression="#status = :pending",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":accepted": "accepted",
                ":pending": "pending",
                ":now": now.isoformat(),
                ":accountId": accepted_by_account_id,
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise InvitationNotPendingError(invitation_id) from exc
        raise
    return resp["Attributes"]
