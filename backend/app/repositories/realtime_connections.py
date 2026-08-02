"""Realtime WebSocket connection registry (catalog §9 `core.realtime_connections`).

Item shape: PK = ``PROFILE#{profileId}``  SK = ``CONNECTION#{connectionId}`` —
listing every live connection for a profile (needed to push server events to
all of that profile's open sockets) is then a direct query, no scan needed.
GSI1 (``GSI1PK=CONNECTION#{connectionId}`` / ``GSI1SK=CONNECTION``) supports
direct lookup by connection id alone, since the `$disconnect` route only ever
carries the connection id, not the profile id.

In AWS this row also carries the API Gateway Management API endpoint needed
for `PostToConnection`; this codebase only ever deploys one WebSocket API
stage so ``api_gateway_endpoint`` is accepted but not required to vary.
"""
from __future__ import annotations

from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.core.dynamodb import GSI1_NAME, get_table


def _pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _sk(connection_id: str) -> str:
    return f"CONNECTION#{connection_id}"


def _strip(item: dict) -> dict:
    return {
        k: v
        for k, v in item.items()
        if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entityType")
    }


def create_connection(
    connection_id: str, account_id: str, profile_id: str, api_gateway_endpoint: str = ""
) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "connection_id": connection_id,
        "account_id": account_id,
        "profile_id": profile_id,
        "api_gateway_endpoint": api_gateway_endpoint,
        "connected_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(profile_id),
            "SK": _sk(connection_id),
            "GSI1PK": f"CONNECTION#{connection_id}",
            "GSI1SK": "CONNECTION",
            "entityType": "RealtimeConnection",
            **item,
        }
    )
    return _strip(item)


def get_connection_by_id(connection_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression=Key("GSI1PK").eq(f"CONNECTION#{connection_id}")
        & Key("GSI1SK").eq("CONNECTION"),
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def list_connections_for_profile(profile_id: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(_pk(profile_id))
        & Key("SK").begins_with("CONNECTION#")
    )
    return [_strip(item) for item in resp.get("Items", [])]


def delete_connection(profile_id: str, connection_id: str) -> None:
    table = get_table()
    table.delete_item(Key={"PK": _pk(profile_id), "SK": _sk(connection_id)})
