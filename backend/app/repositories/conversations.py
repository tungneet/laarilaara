"""Conversation repository (catalog §9 messaging: `GET /v1/conversations`,
`GET /v1/conversations/{conversationId}`, `POST .../read`, `POST .../mute`).

Item shape: PK = ``CONVERSATION#{id}``   SK = ``CONVERSATION``. One
conversation per match (1:1 with the two match participants) — created
automatically when an interest is accepted, see
`app.services.interests.accept_interest`.

`read_markers` and `muted` are per-profile maps (``{profileId: value}``),
initialized empty so nested `UpdateExpression` paths (`read_markers.#pid`,
`muted.#pid`) always have an existing top-level map to write into.

KNOWN SIMPLIFICATION: listing conversations for a profile uses a table
`scan()` with a `FilterExpression` (no per-profile GSI yet) — same accepted
dev/test-scale simplification as `matches.py`/`interests.py`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr

from app.core.dynamodb import get_table


def _pk(conversation_id: str) -> str:
    return f"CONVERSATION#{conversation_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_conversation(match_id: str, profile_a_id: str, profile_b_id: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    conversation_id = uuid.uuid4().hex
    item = {
        "id": conversation_id,
        "match_id": match_id,
        "profile_a_id": profile_a_id,
        "profile_b_id": profile_b_id,
        "last_message_at": None,
        "last_message_preview": None,
        "read_markers": {},
        "muted": {},
        "created_at": now,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={"PK": _pk(conversation_id), "SK": "CONVERSATION", "entityType": "Conversation", **item}
    )
    return item


def get_conversation(conversation_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(conversation_id), "SK": "CONVERSATION"})
    item = resp.get("Item")
    return _strip(item) if item else None


def list_for_profile(profile_id: str) -> list[dict]:
    filter_expr = Attr("entityType").eq("Conversation") & (
        Attr("profile_a_id").eq(profile_id) | Attr("profile_b_id").eq(profile_id)
    )
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
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return [_strip(item) for item in items]


def update_last_message(conversation_id: str, preview: str | None, at: str) -> dict:
    table = get_table()
    resp = table.update_item(
        Key={"PK": _pk(conversation_id), "SK": "CONVERSATION"},
        UpdateExpression="SET last_message_at = :at, last_message_preview = :preview, updated_at = :at",
        ExpressionAttributeValues={":at": at, ":preview": preview},
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])


def set_read_marker(conversation_id: str, profile_id: str, marker: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    resp = table.update_item(
        Key={"PK": _pk(conversation_id), "SK": "CONVERSATION"},
        UpdateExpression="SET read_markers.#pid = :marker, updated_at = :updated_at",
        ExpressionAttributeNames={"#pid": profile_id},
        ExpressionAttributeValues={":marker": marker, ":updated_at": now},
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])


def set_muted(conversation_id: str, profile_id: str, muted: bool) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    resp = table.update_item(
        Key={"PK": _pk(conversation_id), "SK": "CONVERSATION"},
        UpdateExpression="SET muted.#pid = :muted, updated_at = :updated_at",
        ExpressionAttributeNames={"#pid": profile_id},
        ExpressionAttributeValues={":muted": muted, ":updated_at": now},
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])
