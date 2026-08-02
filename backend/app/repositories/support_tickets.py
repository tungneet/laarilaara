"""Support ticket repository (catalog §15 admin billing/support surface).

Unlike almost every other resource in this codebase, support tickets are
created DIRECTLY by an admin action (there is no user-facing "file a
ticket" endpoint anywhere in the catalog) — this is the first admin
resource with a real, reachable create path rather than a queued-forever
gap.

Item shape:  PK = ``SUPPORTTICKET#{id}``  SK = ``SUPPORTTICKET``
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr

from app.core.dynamodb import get_table


def _pk(ticket_id: str) -> str:
    return f"SUPPORTTICKET#{ticket_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_ticket(account_id: str | None, subject: str, body: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    ticket_id = uuid.uuid4().hex
    item = {
        "PK": _pk(ticket_id),
        "SK": "SUPPORTTICKET",
        "entityType": "SupportTicket",
        "id": ticket_id,
        "account_id": account_id,
        "subject": subject,
        "body": body,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_ticket(ticket_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(ticket_id), "SK": "SUPPORTTICKET"})
    item = resp.get("Item")
    return _strip(item) if item else None


def list_tickets(status_filter: str | None = None) -> list[dict]:
    table = get_table()
    items: list[dict] = []
    filter_expr = Attr("entityType").eq("SupportTicket")
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


def update_status(ticket_id: str, new_status: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(ticket_id), "SK": "SUPPORTTICKET"},
        UpdateExpression="SET #status = :status, updated_at = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": new_status, ":now": now},
    )
    ticket = get_ticket(ticket_id)
    assert ticket is not None
    return ticket
