"""Generic admin reference-data repository (catalog §15 "Reference data":
"Reviewed CRUD/deactivate endpoints under `/v1/admin/reference/...`; never
hard-delete used options").

Deliberately generic and keyed by an arbitrary ``list_name`` path segment so
one repository/service/router trio covers every reference-data resource
type the catalog implies (plural "endpoints"), rather than one bespoke
module per list.

KNOWN GAP: this is a NEW, separate DynamoDB-backed store — it is not yet
wired into the existing static Python lists in `app/domain/reference_data.py`
(`VERIFICATION_CHECKS`, `PLANS`) or `app/domain/billing.py` (`PROMO_CODES`).
Connecting those read paths to this admin-editable store is future work;
for now this proves out the CRUD/deactivate admin surface in isolation,
the same "exists but not fully wired" pattern as several other sections.

Item shape:  PK = ``REFERENCEDATA#{listName}``  SK = ``ITEM#{itemId}``
"""
from __future__ import annotations

from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.core.dynamodb import get_table


def _pk(list_name: str) -> str:
    return f"REFERENCEDATA#{list_name}"


def _sk(item_id: str) -> str:
    return f"ITEM#{item_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


class ReferenceDataItemAlreadyExistsError(Exception):
    pass


def create_item(list_name: str, item_id: str, label: str, value: dict | None) -> dict:
    from botocore.exceptions import ClientError

    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _pk(list_name),
        "SK": _sk(item_id),
        "entityType": "ReferenceDataItem",
        "list_name": list_name,
        "id": item_id,
        "label": label,
        "value": value,
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    try:
        table.put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ReferenceDataItemAlreadyExistsError(item_id) from exc
        raise
    return _strip(item)


def get_item(list_name: str, item_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(list_name), "SK": _sk(item_id)})
    item = resp.get("Item")
    return _strip(item) if item else None


def list_items(list_name: str, include_inactive: bool = False) -> list[dict]:
    table = get_table()
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(_pk(list_name)) & Key("SK").begins_with("ITEM#")
    )
    items = [_strip(item) for item in resp.get("Items", [])]
    if not include_inactive:
        items = [item for item in items if item.get("active", True)]
    return items


def update_item(list_name: str, item_id: str, label: str | None, value: dict | None) -> dict | None:
    existing = get_item(list_name, item_id)
    if existing is None:
        return None
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    new_label = label if label is not None else existing["label"]
    new_value = value if value is not None else existing.get("value")
    table.update_item(
        Key={"PK": _pk(list_name), "SK": _sk(item_id)},
        UpdateExpression="SET label = :label, #value = :value, updated_at = :now",
        ExpressionAttributeNames={"#value": "value"},
        ExpressionAttributeValues={":label": new_label, ":value": new_value, ":now": now},
    )
    return get_item(list_name, item_id)


def deactivate_item(list_name: str, item_id: str) -> dict | None:
    existing = get_item(list_name, item_id)
    if existing is None:
        return None
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(list_name), "SK": _sk(item_id)},
        UpdateExpression="SET active = :active, updated_at = :now",
        ExpressionAttributeValues={":active": False, ":now": now},
    )
    return get_item(list_name, item_id)
