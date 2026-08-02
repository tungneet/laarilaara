"""Promo redemption repository (catalog §13: `POST /v1/promo-redemptions`).

Item shape: PK = ``ACCOUNT#{accountId}``  SK = ``PROMOREDEMPTION#{code}``
Idempotent upsert keyed by code — redeeming the same code twice returns the
same record rather than erroring, same convention as
`app/repositories/moderation_actions.py::put_appeal`.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _sk(code: str) -> str:
    return f"PROMOREDEMPTION#{code}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def get_redemption(account_id: str, code: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(account_id), "SK": _sk(code)})
    item = resp.get("Item")
    return _strip(item) if item else None


def put_redemption(account_id: str, code: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    fields = {"account_id": account_id, "code": code, "status": "applied", "applied_at": now}
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _sk(code),
            "entityType": "PromoRedemption",
            **fields,
        }
    )
    return fields
