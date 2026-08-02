"""Media asset repository (catalog §6: `POST /v1/uploads`,
`POST /v1/uploads/{uploadId}/complete`, `GET/DELETE /v1/media/{assetId}`).

Item shape:  PK = ``MEDIAASSET#{assetId}``   SK = ``MEDIAASSET``
GSI1 (idempotency lookup by owner+checksum):
  GSI1PK = ``ACCOUNTCHECKSUM#{accountId}#{checksum}``   GSI1SK = ``MEDIAASSET``

``status`` is a DynamoDB reserved word — always aliased via
``ExpressionAttributeNames`` (``#status``) in update expressions, never used
bare (see standing repo convention).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import GSI1_NAME, get_table


class AssetNotFoundError(Exception):
    pass


class InvalidAssetStateError(Exception):
    def __init__(self, current_status: str) -> None:
        super().__init__(f"invalid asset state: {current_status}")
        self.current_status = current_status


def _pk(asset_id: str) -> str:
    return f"MEDIAASSET#{asset_id}"


_SK = "MEDIAASSET"


def _checksum_gsi1pk(account_id: str, checksum: str) -> str:
    return f"ACCOUNTCHECKSUM#{account_id}#{checksum}"


def _strip(item: dict) -> dict:
    return {
        k: v
        for k, v in item.items()
        if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entityType", "storage_key")
    }


def create_upload(
    account_id: str,
    purpose: str,
    content_type: str,
    size_bytes: int,
    checksum: str,
) -> dict:
    asset_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc).isoformat()
    storage_key = f"uploads/{account_id}/{asset_id}"
    fields = {
        "id": asset_id,
        "account_id": account_id,
        "purpose": purpose,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "checksum": checksum,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(asset_id),
            "SK": _SK,
            "GSI1PK": _checksum_gsi1pk(account_id, checksum),
            "GSI1SK": _SK,
            "entityType": "MediaAsset",
            "storage_key": storage_key,
            **fields,
        }
    )
    return {**fields, "storage_key": storage_key}


def get_asset(asset_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(asset_id), "SK": _SK})
    item = resp.get("Item")
    if item is None:
        return None
    return {**_strip(item), "storage_key": item["storage_key"]}


def find_by_account_checksum(account_id: str, checksum: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName=GSI1_NAME,
        KeyConditionExpression="GSI1PK = :gsi1pk AND GSI1SK = :gsi1sk",
        ExpressionAttributeValues={
            ":gsi1pk": _checksum_gsi1pk(account_id, checksum),
            ":gsi1sk": _SK,
        },
    )
    items = resp.get("Items", [])
    if not items:
        return None
    return {**_strip(items[0]), "storage_key": items[0]["storage_key"]}


def mark_ready(asset_id: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    table = get_table()
    try:
        table.update_item(
            Key={"PK": _pk(asset_id), "SK": _SK},
            UpdateExpression="SET #status = :ready, updated_at = :now",
            ConditionExpression="#status = :pending",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":ready": "ready", ":pending": "pending", ":now": now},
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            existing = get_asset(asset_id)
            current_status = existing["status"] if existing else "unknown"
            raise InvalidAssetStateError(current_status) from exc
        raise
    asset = get_asset(asset_id)
    assert asset is not None
    return asset


def soft_delete(asset_id: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    table = get_table()
    table.update_item(
        Key={"PK": _pk(asset_id), "SK": _SK},
        UpdateExpression="SET #status = :deleted, updated_at = :now",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":deleted": "deleted", ":now": now},
    )
    asset = get_asset(asset_id)
    assert asset is not None
    return asset
