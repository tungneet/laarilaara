"""Interest repository (catalog §8).

Item shape:  PK = ``INTEREST#{id}``   SK = ``INTEREST``

KNOWN SIMPLIFICATION: like `profiles_repo.list_published_profiles`, listing
and idempotency lookups use a table `scan()` with a `FilterExpression`
rather than a secondary index — there is no per-profile GSI for interests
yet, and this codebase already accepts full-table scans at dev/test scale
for §7 discovery. Revisit with a real index before production scale.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr

from app.core.dynamodb import get_table


def _pk(interest_id: str) -> str:
    return f"INTEREST#{interest_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def get_interest(interest_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(interest_id), "SK": "INTEREST"})
    item = resp.get("Item")
    return _strip(item) if item else None


def find_pending(from_profile_id: str, to_profile_id: str) -> dict | None:
    table = get_table()
    resp = table.scan(
        FilterExpression=(
            Attr("entityType").eq("Interest")
            & Attr("from_profile_id").eq(from_profile_id)
            & Attr("to_profile_id").eq(to_profile_id)
            & Attr("status").eq("pending")
        )
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def create_interest(from_profile_id: str, to_profile_id: str, message: str | None) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    interest_id = uuid.uuid4().hex
    item = {
        "id": interest_id,
        "from_profile_id": from_profile_id,
        "to_profile_id": to_profile_id,
        "message": message,
        "status": "pending",
        "decline_reason": None,
        "created_at": now,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(interest_id),
            "SK": "INTEREST",
            "entityType": "Interest",
            **item,
        }
    )
    return item


def list_for_profile(profile_id: str, direction: str, status: str | None) -> list[dict]:
    """``direction`` is ``"outgoing"`` (from this profile) or ``"incoming"``
    (to this profile). Results are sorted by ``created_at`` ascending."""
    field = "from_profile_id" if direction == "outgoing" else "to_profile_id"
    filter_expr = Attr("entityType").eq("Interest") & Attr(field).eq(profile_id)
    if status is not None:
        filter_expr = filter_expr & Attr("status").eq(status)

    table = get_table()
    items: list[dict] = []
    scan_kwargs: dict = {"FilterExpression": filter_expr}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    items.sort(key=lambda item: item["created_at"])
    return [_strip(item) for item in items]


def update_status(interest_id: str, new_status: str, *, decline_reason: str | None = None) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    update_expr = "SET #status = :status, updated_at = :updated_at"
    values: dict = {":status": new_status, ":updated_at": now}
    if decline_reason is not None:
        update_expr += ", decline_reason = :decline_reason"
        values[":decline_reason"] = decline_reason
    resp = table.update_item(
        Key={"PK": _pk(interest_id), "SK": "INTEREST"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])
