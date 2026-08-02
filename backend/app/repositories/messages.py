"""Message repository (catalog §9 messaging: `GET/POST /v1/conversations/{id}/messages`,
`PATCH/DELETE /v1/conversations/{id}/messages/{messageId}`).

Item shape: PK = ``CONVERSATION#{conversationId}``
            SK = ``MESSAGE#{sortKey}#{messageId}``
where `sortKey` is a fixed-width UTC timestamp (`%Y%m%dT%H%M%S%f`) rather than
`datetime.isoformat()`, because `isoformat()` omits the microsecond component
when it is zero — that would break lexicographic SK ordering. `sort_key` is
also stored as a plain attribute (not stripped from responses, silently
ignored by response schemas) so the service layer can reconstruct the SK for
`update_body`/`soft_delete` without a second lookup.

GSI1 (``GSI1PK=MESSAGE#{id}`` / ``GSI1SK=MESSAGE``) supports direct lookup by
message id for edit/delete, mirroring the challenge-lookup-by-id pattern
used elsewhere in this codebase.

KNOWN SIMPLIFICATION: `list_messages` fetches a conversation's full message
set via `Query` (chronological, paginated internally via `LastEvaluatedKey`),
then the service layer applies the shared `app.core.pagination` offset-cursor
— same accepted dev/test-scale simplification as §7/§8 list endpoints, not
the catalog's true keyset/directional cursor.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr, Key

from app.core.dynamodb import GSI1_NAME, get_table


def _pk(conversation_id: str) -> str:
    return f"CONVERSATION#{conversation_id}"


def _sort_key(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S%f")


def _sk(sort_key: str, message_id: str) -> str:
    return f"MESSAGE#{sort_key}#{message_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entityType")}


def create_message(
    conversation_id: str,
    sender_profile_id: str,
    client_message_id: str,
    body: str | None,
    attachment_asset_id: str | None,
) -> dict:
    now = datetime.now(tz=timezone.utc)
    now_iso = now.isoformat()
    message_id = uuid.uuid4().hex
    sort_key = _sort_key(now)
    item = {
        "id": message_id,
        "conversation_id": conversation_id,
        "sender_profile_id": sender_profile_id,
        "client_message_id": client_message_id,
        "body": body,
        "attachment_asset_id": attachment_asset_id,
        "status": "sent",
        "revision": 1,
        "sort_key": sort_key,
        "created_at": now_iso,
        "updated_at": now_iso,
        "edited_at": None,
        "deleted_at": None,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(conversation_id),
            "SK": _sk(sort_key, message_id),
            "GSI1PK": f"MESSAGE#{message_id}",
            "GSI1SK": "MESSAGE",
            "entityType": "Message",
            **item,
        }
    )
    return item


def find_by_client_message_id(
    conversation_id: str, sender_profile_id: str, client_message_id: str
) -> dict | None:
    table = get_table()
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(_pk(conversation_id)) & Key("SK").begins_with("MESSAGE#"),
        FilterExpression=(
            Attr("sender_profile_id").eq(sender_profile_id)
            & Attr("client_message_id").eq(client_message_id)
        ),
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def get_message_by_id(message_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression=Key("GSI1PK").eq(f"MESSAGE#{message_id}") & Key("GSI1SK").eq("MESSAGE"),
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def list_messages(conversation_id: str) -> list[dict]:
    table = get_table()
    items: list[dict] = []
    query_kwargs: dict = {
        "KeyConditionExpression": Key("PK").eq(_pk(conversation_id)) & Key("SK").begins_with("MESSAGE#"),
        "ScanIndexForward": True,
    }
    while True:
        resp = table.query(**query_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key
    return [_strip(item) for item in items]


def update_body(conversation_id: str, message_id: str, sort_key: str, body: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    resp = table.update_item(
        Key={"PK": _pk(conversation_id), "SK": _sk(sort_key, message_id)},
        UpdateExpression=(
            "SET body = :body, #status = :status, updated_at = :updated_at, "
            "edited_at = :edited_at, revision = revision + :one"
        ),
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":body": body,
            ":status": "edited",
            ":updated_at": now,
            ":edited_at": now,
            ":one": 1,
        },
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])


def soft_delete(conversation_id: str, message_id: str, sort_key: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    resp = table.update_item(
        Key={"PK": _pk(conversation_id), "SK": _sk(sort_key, message_id)},
        UpdateExpression=(
            "SET #status = :status, body = :body, updated_at = :updated_at, deleted_at = :deleted_at"
        ),
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "deleted",
            ":body": None,
            ":updated_at": now,
            ":deleted_at": now,
        },
        ReturnValues="ALL_NEW",
    )
    return _strip(resp["Attributes"])
