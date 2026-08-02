"""Push endpoint repository (catalog §12:
`POST /v1/push-endpoints`, `DELETE /v1/push-endpoints/{endpointId}`).

Item shape: PK = ``ACCOUNT#{accountId}``  SK = ``PUSHENDPOINT#{id}``
GSI1 (``GSI1PK=PUSHENDPOINT#{id}`` / ``GSI1SK=PUSHENDPOINT``) supports direct
lookup by id for delete, mirroring the message-lookup-by-id pattern — the
delete route only carries the endpoint id, not the account, so ownership is
re-checked in the service layer via the account id stored on the item.

The raw provider token is stored but never returned in any response (catalog:
"do not reveal provider destination or delivery internals").
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.core.dynamodb import GSI1_NAME, get_table


def _pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _sk(endpoint_id: str) -> str:
    return f"PUSHENDPOINT#{endpoint_id}"


def _strip(item: dict) -> dict:
    return {
        k: v
        for k, v in item.items()
        if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entityType", "token")
    }


def create_endpoint(account_id: str, platform: str, token: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    endpoint_id = uuid.uuid4().hex
    item = {
        "id": endpoint_id,
        "account_id": account_id,
        "platform": platform,
        "token": token,
        "created_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _sk(endpoint_id),
            "GSI1PK": f"PUSHENDPOINT#{endpoint_id}",
            "GSI1SK": "PUSHENDPOINT",
            "entityType": "PushEndpoint",
            **item,
        }
    )
    return _strip(item)


def get_endpoint_by_id(endpoint_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression=Key("GSI1PK").eq(f"PUSHENDPOINT#{endpoint_id}")
        & Key("GSI1SK").eq("PUSHENDPOINT"),
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def delete_endpoint(account_id: str, endpoint_id: str) -> None:
    table = get_table()
    table.delete_item(Key={"PK": _pk(account_id), "SK": _sk(endpoint_id)})
