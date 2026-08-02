"""Notification preferences repository (catalog §12:
`GET/PUT /v1/notification-preferences`).

Item shape: PK = ``ACCOUNT#{accountId}``  SK = ``NOTIFICATIONPREFERENCES``
Full-replace semantics on PUT, same convention as
`app/repositories/profile_sections.py::replace_section`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table

_SK = "NOTIFICATIONPREFERENCES"


def _pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def get_preferences(account_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(account_id), "SK": _SK})
    item = resp.get("Item")
    if item is None:
        return None
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def put_preferences(account_id: str, categories: dict) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    fields = {"account_id": account_id, "categories": categories, "updated_at": now}
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _SK,
            "entityType": "NotificationPreferences",
            **fields,
        }
    )
    return fields
