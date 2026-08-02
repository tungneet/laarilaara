"""Data request repository (DynamoDB single-table).

Data request item:
    PK = ``ACCOUNT#{accountId}``   SK = ``DATAREQUEST#{requestId}``

Models an export/correction/deletion request per catalog §4. No async
worker exists yet to actually process these — every request is created in the
``queued`` state (matching the shared Operation resource's state machine in
catalog §2) and stays there until a future worker picks it up.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _account_pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _request_sk(request_id: str) -> str:
    return f"DATAREQUEST#{request_id}"


def create_data_request(account_id: str, request_type: str, details: str | None) -> dict:
    table = get_table()
    request_id = uuid.uuid4().hex
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _account_pk(account_id),
        "SK": _request_sk(request_id),
        "entityType": "DataRequest",
        "id": request_id,
        "accountId": account_id,
        "type": request_type,
        "status": "queued",
        "details": details,
        "createdAt": now,
        "completedAt": None,
    }
    table.put_item(Item=item)
    return item


def get_data_request(account_id: str, request_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(
        Key={"PK": _account_pk(account_id), "SK": _request_sk(request_id)}
    )
    return resp.get("Item")
