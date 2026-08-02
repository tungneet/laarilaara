"""Webhook event repository (catalog §14: durable capture of inbound
provider webhook events for billing/verification/notifications).

Item shape: PK = ``WEBHOOKEVENT#{kind}#{provider}#{externalId}``
SK = ``WEBHOOKEVENT``. Keying by the provider's own unique external event ID
(not a generated UUID) makes the durable capture itself idempotent — a
conditional put (`attribute_not_exists(PK)`) is the "unique external ID"
de-duplication step called out in the catalog notes.

KNOWN GAP (same class as reports/notifications/billing-transactions): no
async worker exists to process captured events further — this repository
only durably records that an event was received and verified; nothing reads
these rows back today except tests.
"""
from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import get_table


def _pk(kind: str, provider: str, external_id: str) -> str:
    return f"WEBHOOKEVENT#{kind}#{provider}#{external_id}"


_SK = "WEBHOOKEVENT"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def get_event(kind: str, provider: str, external_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(kind, provider, external_id), "SK": _SK})
    item = resp.get("Item")
    return _strip(item) if item else None


def capture_event(kind: str, provider: str, external_id: str, payload: dict) -> tuple[dict, bool]:
    """Durably store a verified event. Returns ``(item, created)`` — if the
    external ID was already captured, returns the existing item with
    ``created=False`` instead of raising (idempotent fast-ack).
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "kind": kind,
        "provider": provider,
        "external_id": external_id,
        "payload": payload,
        "received_at": now,
    }
    table = get_table()
    try:
        table.put_item(
            Item={
                "PK": _pk(kind, provider, external_id),
                "SK": _SK,
                "entityType": "WebhookEvent",
                **item,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            existing = get_event(kind, provider, external_id)
            return existing or item, False
        raise
    return item, True
