"""Immutable admin audit log (catalog §15: "reason capture for sensitive
reads/actions... immutable audit").

Append-only: there is deliberately no update/delete function here. Every
mutating admin service function calls `record(...)` after (or as part of)
its write. There is no dedicated list/read endpoint in the baseline catalog
for this resource, so it is write-only from the API's point of view for now
(a future admin "audit trail" viewer would read the same rows).

Item shape:  PK = ``ADMINAUDIT#{adminAccountId}``  SK = ``EVENT#{sortKey}#{id}``
Newest-first ordering uses the same microsecond sort-key convention as
`notification_center.py`/`billing.py` transactions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(admin_account_id: str) -> str:
    return f"ADMINAUDIT#{admin_account_id}"


def record(
    admin_account_id: str,
    action: str,
    target_type: str,
    target_id: str,
    reason: str,
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    sort_key = now.strftime("%Y%m%dT%H%M%S%f")
    event_id = uuid.uuid4().hex
    item = {
        "PK": _pk(admin_account_id),
        "SK": f"EVENT#{sort_key}#{event_id}",
        "entityType": "AdminAuditEvent",
        "id": event_id,
        "admin_account_id": admin_account_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "reason": reason,
        "created_at": now.isoformat(),
    }
    table.put_item(Item=item)
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}
