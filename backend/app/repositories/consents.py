"""Consent repository (DynamoDB single-table).

Consent decisions are append-only: every decision creates a brand-new item,
never overwritten, so there is a full audit trail. Item shape:

    PK = ``ACCOUNT#{accountId}``   SK = ``CONSENT#{consentType}#{isoTimestamp}``

The ISO-8601 timestamp component keeps items naturally sorted chronologically
within a `Query`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _account_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def record_consent(
    account_id: str, consent_type: str, granted: bool, policy_version: str
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    decided_at = now.isoformat()
    item = {
        "PK": _account_pk(account_id),
        "SK": f"CONSENT#{consent_type}#{decided_at}",
        "entityType": "Consent",
        "id": uuid.uuid4().hex,
        "accountId": account_id,
        "consentType": consent_type,
        "granted": granted,
        "policyVersion": policy_version,
        "decidedAt": decided_at,
    }
    table.put_item(Item=item)
    return item


def list_consents(account_id: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={
            ":pk": _account_pk(account_id),
            ":sk_prefix": "CONSENT#",
        },
    )
    return resp.get("Items", [])
