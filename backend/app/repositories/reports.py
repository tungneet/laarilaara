"""Report repository (catalog §11: `POST /v1/reports`, `GET /v1/reports/{id}`).

Item shape:  PK = ``REPORT#{id}``   SK = ``REPORT``

No moderation worker exists anywhere in this codebase yet (same class of gap
as `ai_artifacts.py`/`data_requests.py`), so every report is created with
``status="queued"`` and never transitions further. See
`app/services/reports.py` for the reporter-safe read shape.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(report_id: str) -> str:
    return f"REPORT#{report_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_report(
    reporter_profile_id: str,
    subject_type: str,
    subject_id: str,
    reason: str,
    details: str | None,
    evidence_asset_ids: list[str],
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    report_id = str(uuid.uuid4())
    item = {
        "PK": _pk(report_id),
        "SK": "REPORT",
        "entityType": "Report",
        "id": report_id,
        "reporter_profile_id": reporter_profile_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "reason": reason,
        "details": details,
        "evidence_asset_ids": evidence_asset_ids,
        "status": "queued",
        "created_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_report(report_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(report_id), "SK": "REPORT"})
    item = resp.get("Item")
    return _strip(item) if item else None
