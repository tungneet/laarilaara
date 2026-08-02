"""Generic profile -> target-profile keyed link repository (catalog §7:
shortlist and hidden-profiles — both "one row per (actingProfile,
targetProfile)" collections with idempotent PUT/DELETE semantics, keyed by
the caller-supplied target profile id rather than a generated record id).

Item shape:  PK = ``PROFILE#{profileId}``   SK = ``{KIND}#{targetProfileId}``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _sk(kind: str, target_profile_id: str) -> str:
    return f"{kind}#{target_profile_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def list_links(profile_id: str, kind: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":pk": _pk(profile_id), ":sk_prefix": f"{kind}#"},
    )
    return [_strip(item) for item in resp.get("Items", [])]


def get_link(profile_id: str, kind: str, target_profile_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(profile_id), "SK": _sk(kind, target_profile_id)})
    item = resp.get("Item")
    return _strip(item) if item else None


def put_link(profile_id: str, kind: str, target_profile_id: str, fields: dict) -> dict:
    """Idempotent upsert: preserves the original ``created_at`` if the link
    already exists, always refreshes ``updated_at`` and the given fields."""
    existing = get_link(profile_id, kind, target_profile_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    created_at = existing["created_at"] if existing else now
    item = {
        "target_profile_id": target_profile_id,
        **fields,
        "created_at": created_at,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(profile_id),
            "SK": _sk(kind, target_profile_id),
            "entityType": "ProfileTargetLink",
            **item,
        }
    )
    return item


def delete_link(profile_id: str, kind: str, target_profile_id: str) -> None:
    """Idempotent: succeeds silently if the link does not exist."""
    table = get_table()
    table.delete_item(Key={"PK": _pk(profile_id), "SK": _sk(kind, target_profile_id)})
