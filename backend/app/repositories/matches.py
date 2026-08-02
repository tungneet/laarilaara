"""Match repository (catalog §8).

Item shapes:
  Match:    PK = ``MATCH#{id}``   SK = ``MATCH``
  Feedback: PK = ``MATCH#{id}``   SK = ``FEEDBACK#{authorProfileId}`` (upsert, one per author)
  Outcome:  PK = ``MATCH#{id}``   SK = ``OUTCOME#{authorProfileId}`` (upsert, one per author)

KNOWN SIMPLIFICATION: listing matches for a profile uses a table `scan()`
with a `FilterExpression` (no per-profile GSI yet) — same accepted
dev/test-scale simplification as `interests.py` and §7 discovery.

``conversation_id`` starts ``None`` and is filled in by
`set_conversation_id` once `app.services.interests.accept_interest` creates
the accompanying conversation (catalog §9 messaging).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr

from app.core.dynamodb import get_table


def _pk(match_id: str) -> str:
    return f"MATCH#{match_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_match(interest_id: str, profile_a_id: str, profile_b_id: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    match_id = uuid.uuid4().hex
    item = {
        "id": match_id,
        "interest_id": interest_id,
        "profile_a_id": profile_a_id,
        "profile_b_id": profile_b_id,
        "status": "active",
        "conversation_id": None,
        "created_at": now,
        "updated_at": now,
        "ended_at": None,
    }
    table = get_table()
    table.put_item(Item={"PK": _pk(match_id), "SK": "MATCH", "entityType": "Match", **item})
    return item


def get_match(match_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(match_id), "SK": "MATCH"})
    item = resp.get("Item")
    return _strip(item) if item else None


def list_for_profile(profile_id: str, status: str | None) -> list[dict]:
    filter_expr = Attr("entityType").eq("Match") & (
        Attr("profile_a_id").eq(profile_id) | Attr("profile_b_id").eq(profile_id)
    )
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


def set_conversation_id(match_id: str, conversation_id: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    resp = table.update_item(
        Key={"PK": _pk(match_id), "SK": "MATCH"},
        UpdateExpression="SET conversation_id = :cid, updated_at = :updated_at",
        ExpressionAttributeValues={":cid": conversation_id, ":updated_at": now},
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])


def end_match(match_id: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    resp = table.update_item(
        Key={"PK": _pk(match_id), "SK": "MATCH"},
        UpdateExpression="SET #status = :status, updated_at = :updated_at, ended_at = :ended_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "ended",
            ":updated_at": now,
            ":ended_at": now,
        },
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])


def put_feedback(match_id: str, author_profile_id: str, fields: dict) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {"author_profile_id": author_profile_id, **fields, "created_at": now}
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(match_id),
            "SK": f"FEEDBACK#{author_profile_id}",
            "entityType": "MatchFeedback",
            **item,
        }
    )
    return item


def put_outcome(match_id: str, author_profile_id: str, fields: dict) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {"author_profile_id": author_profile_id, **fields, "created_at": now}
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(match_id),
            "SK": f"OUTCOME#{author_profile_id}",
            "entityType": "MatchOutcome",
            **item,
        }
    )
    return item
