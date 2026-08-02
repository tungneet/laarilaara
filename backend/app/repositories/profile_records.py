"""Generic list/CRUD profile record repository (catalog §5 — "Sections"
batch C: education, employment — both "list/add records, change/remove one
record" resources with the same shape).

Item shape:  PK = ``PROFILE#{profileId}``   SK = ``{KIND}#{recordId}``
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import get_table


class RecordNotFoundError(Exception):
    pass


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _record_sk(kind: str, record_id: str) -> str:
    return f"{kind}#{record_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def list_records(profile_id: str, kind: str) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
        ExpressionAttributeValues={":pk": _profile_pk(profile_id), ":sk_prefix": f"{kind}#"},
    )
    return [_strip(item) for item in resp.get("Items", [])]


def create_record(profile_id: str, kind: str, fields: dict) -> dict:
    record_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "id": record_id,
        **fields,
        "created_at": now,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _profile_pk(profile_id),
            "SK": _record_sk(kind, record_id),
            "entityType": "ProfileRecord",
            **item,
        }
    )
    return item


def get_record(profile_id: str, kind: str, record_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(
        Key={"PK": _profile_pk(profile_id), "SK": _record_sk(kind, record_id)}
    )
    item = resp.get("Item")
    return _strip(item) if item else None


def update_record(profile_id: str, kind: str, record_id: str, updates: dict) -> dict:
    existing = get_record(profile_id, kind, record_id)
    if existing is None:
        raise RecordNotFoundError(record_id)
    merged = {**existing, **{k: v for k, v in updates.items() if v is not None}}
    merged["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    table = get_table()
    try:
        table.put_item(
            Item={
                "PK": _profile_pk(profile_id),
                "SK": _record_sk(kind, record_id),
                "entityType": "ProfileRecord",
                **merged,
            },
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RecordNotFoundError(record_id) from exc
        raise
    return merged


def delete_record(profile_id: str, kind: str, record_id: str) -> None:
    table = get_table()
    try:
        table.delete_item(
            Key={"PK": _profile_pk(profile_id), "SK": _record_sk(kind, record_id)},
            ConditionExpression="attribute_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise RecordNotFoundError(record_id) from exc
        raise
