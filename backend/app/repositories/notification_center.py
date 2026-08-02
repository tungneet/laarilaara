"""In-app notification repository (catalog §12: `GET /v1/notifications`,
`POST /v1/notifications/{id}/read`, `POST /v1/notifications/read-all`).

Item shape: PK = ``ACCOUNT#{accountId}``  SK = ``NOTIFICATION#{sortKey}#{id}``
where `sortKey` is a fixed-width UTC timestamp (`%Y%m%dT%H%M%S%f`), same
gotcha/convention as `app/repositories/messages.py` (`isoformat()` would omit
the microsecond component when it's exactly zero, breaking lexicographic
ordering).

GSI1 (``GSI1PK=NOTIFICATION#{id}`` / ``GSI1SK=NOTIFICATION``) supports direct
lookup by id for the "mark one read" endpoint, mirroring the
message-lookup-by-id pattern.

No SQS-triggered notification worker exists in this codebase yet (catalog
§12 says delivery happens there) — `create_notification` exists for
tests/future worker reuse; nothing in the running API creates notifications
today, same class of gap as `app/repositories/moderation_actions.py`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.core.dynamodb import GSI1_NAME, get_table


def _pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _sort_key(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S%f")


def _sk(sort_key: str, notification_id: str) -> str:
    return f"NOTIFICATION#{sort_key}#{notification_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entityType")}


def create_notification(
    account_id: str, category: str, title: str, body: str, data: dict | None
) -> dict:
    now = datetime.now(tz=timezone.utc)
    now_iso = now.isoformat()
    notification_id = uuid.uuid4().hex
    sort_key = _sort_key(now)
    item = {
        "id": notification_id,
        "account_id": account_id,
        "category": category,
        "title": title,
        "body": body,
        "data": data or {},
        "created_at": now_iso,
        "read_at": None,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _sk(sort_key, notification_id),
            "GSI1PK": f"NOTIFICATION#{notification_id}",
            "GSI1SK": "NOTIFICATION",
            "entityType": "Notification",
            **item,
        }
    )
    return item


def get_notification_by_id(notification_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression=Key("GSI1PK").eq(f"NOTIFICATION#{notification_id}")
        & Key("GSI1SK").eq("NOTIFICATION"),
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def list_notifications(account_id: str) -> list[dict]:
    """Newest first — an in-app inbox reads better most-recent-on-top,
    unlike the chronological (oldest-first) chat message list.
    """
    table = get_table()
    items: list[dict] = []
    query_kwargs: dict = {
        "KeyConditionExpression": Key("PK").eq(_pk(account_id)) & Key("SK").begins_with("NOTIFICATION#"),
        "ScanIndexForward": False,
    }
    while True:
        resp = table.query(**query_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key
    return [_strip(item) for item in items]


def mark_read(account_id: str, sort_key: str, notification_id: str) -> None:
    table = get_table()
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(account_id), "SK": _sk(sort_key, notification_id)},
        UpdateExpression="SET read_at = :read_at",
        ExpressionAttributeValues={":read_at": now_iso},
    )
