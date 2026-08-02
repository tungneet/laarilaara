"""Moderation case repository (catalog §15 admin moderation surface).

Distinct from `moderation_actions.py` (catalog §11): a *case* is the admin
work-queue wrapper (assign/act/close workflow) around a subject account,
optionally seeded from an existing `Report` (§11's `reports.py`, which is
itself another "queued forever, no worker" resource until now). Posting an
action against a case creates a real `ModerationAction` row via
`moderation_actions_repo.create_action`, finally giving reports a real
downstream consequence.

There is no admin-facing "create case" endpoint in the baseline catalog —
cases are expected to be raised from the reports queue (or other signals)
by an out-of-band process. `create_case` exists for that future wiring and
for direct test seeding (white-box pattern, same as `moderation_actions.py`).

Item shape:  PK = ``MODERATIONCASE#{id}``  SK = ``MODERATIONCASE``
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr

from app.core.dynamodb import get_table


def _pk(case_id: str) -> str:
    return f"MODERATIONCASE#{case_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_case(subject_account_id: str, report_id: str | None = None) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    case_id = uuid.uuid4().hex
    item = {
        "PK": _pk(case_id),
        "SK": "MODERATIONCASE",
        "entityType": "ModerationCase",
        "id": case_id,
        "subject_account_id": subject_account_id,
        "report_id": report_id,
        "status": "open",
        "assigned_admin_id": None,
        "created_at": now,
        "updated_at": now,
        "closed_at": None,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_case(case_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(case_id), "SK": "MODERATIONCASE"})
    item = resp.get("Item")
    return _strip(item) if item else None


def list_cases(status_filter: str | None = None) -> list[dict]:
    table = get_table()
    items: list[dict] = []
    filter_expr = Attr("entityType").eq("ModerationCase")
    if status_filter:
        filter_expr = filter_expr & Attr("status").eq(status_filter)
    scan_kwargs: dict = {"FilterExpression": filter_expr}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return [_strip(item) for item in items]


def assign_case(case_id: str, admin_account_id: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(case_id), "SK": "MODERATIONCASE"},
        UpdateExpression="SET #status = :status, assigned_admin_id = :admin, updated_at = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "assigned",
            ":admin": admin_account_id,
            ":now": now,
        },
    )
    case = get_case(case_id)
    assert case is not None
    return case


def close_case(case_id: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(case_id), "SK": "MODERATIONCASE"},
        UpdateExpression="SET #status = :status, updated_at = :now, closed_at = :closed_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "closed",
            ":now": now,
            ":closed_at": now,
        },
    )
    case = get_case(case_id)
    assert case is not None
    return case
