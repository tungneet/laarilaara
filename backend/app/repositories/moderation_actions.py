"""Moderation action + appeal repository (catalog §11 appeals endpoint, and
catalog §15 admin surface).

There is no admin decision endpoint yet anywhere in this codebase (§15
admin routes are entirely unbuilt), so nothing in the running API ever
creates a `ModerationAction` — `create_action` exists for tests and for the
future admin-decision service to call. Appeals can still be exercised
end-to-end against a directly-seeded action (white-box test pattern, same
as `test_media.py` simulating a presigned upload via a direct S3 put).

Item shapes:

- Action: ``PK = MODERATIONACTION#{id}``  ``SK = MODERATIONACTION``
- Appeal: ``PK = MODERATIONACTION#{id}``  ``SK = APPEAL#{accountId}``
  One row per (action, appealing account) — resubmission overwrites
  (idempotent upsert, same convention as `ai_artifacts.py` feedback rows).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(action_id: str) -> str:
    return f"MODERATIONACTION#{action_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_action(affected_account_id: str, action_type: str, reason: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    action_id = str(uuid.uuid4())
    item = {
        "PK": _pk(action_id),
        "SK": "MODERATIONACTION",
        "entityType": "ModerationAction",
        "id": action_id,
        "affected_account_id": affected_account_id,
        "action_type": action_type,
        "reason": reason,
        "created_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_action(action_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(action_id), "SK": "MODERATIONACTION"})
    item = resp.get("Item")
    return _strip(item) if item else None


def put_appeal(action_id: str, account_id: str, reason: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _pk(action_id),
        "SK": f"APPEAL#{account_id}",
        "entityType": "ModerationAppeal",
        "action_id": action_id,
        "account_id": account_id,
        "reason": reason,
        "status": "queued",
        "created_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)
