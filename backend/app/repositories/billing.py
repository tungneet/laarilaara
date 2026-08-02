"""Billing repository (catalog §13): checkout sessions, subscription,
and transaction history — three item shapes, one file since they're all
tightly coupled "billing" state for a single account.

No real payment provider is wired up (§14 webhooks are a separate, also
unbuilt, catalog section) — checkout sessions never transition past
``pending`` and the subscription always reflects the account's own ``tier``
field (see `app/domain/accounts.py`), same "queued forever, no worker" class
of gap as reports/verification-requests/notifications. `create_transaction`
exists for tests/future-webhook-worker reuse only; nothing in the running
API creates transaction rows today.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.core.dynamodb import get_table


def _pk(account_id: str) -> str:
    return f"ACCOUNT#{account_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


# ---- Checkout sessions ------------------------------------------------------


def _checkout_sk(session_id: str) -> str:
    return f"CHECKOUTSESSION#{session_id}"


def create_checkout_session(account_id: str, plan_id: str, checkout_url: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    session_id = uuid.uuid4().hex
    item = {
        "id": session_id,
        "account_id": account_id,
        "plan_id": plan_id,
        "status": "pending",
        "checkout_url": checkout_url,
        "created_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _checkout_sk(session_id),
            "entityType": "CheckoutSession",
            **item,
        }
    )
    return item


def find_open_checkout_session(account_id: str, plan_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(_pk(account_id)) & Key("SK").begins_with("CHECKOUTSESSION#"),
    )
    for item in resp.get("Items", []):
        if item.get("plan_id") == plan_id and item.get("status") == "pending":
            return _strip(item)
    return None


# ---- Subscription (single item per account) --------------------------------

_SUBSCRIPTION_SK = "SUBSCRIPTION"


def get_subscription(account_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(account_id), "SK": _SUBSCRIPTION_SK})
    item = resp.get("Item")
    return _strip(item) if item else None


def put_subscription(account_id: str, plan_id: str, status: str, cancel_at_period_end: bool) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    fields = {
        "account_id": account_id,
        "plan_id": plan_id,
        "status": status,
        "cancel_at_period_end": cancel_at_period_end,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _SUBSCRIPTION_SK,
            "entityType": "Subscription",
            **fields,
        }
    )
    return fields


# ---- Transactions (list only, newest first) --------------------------------


def _transaction_sk(sort_key: str, transaction_id: str) -> str:
    return f"TRANSACTION#{sort_key}#{transaction_id}"


def create_transaction(
    account_id: str, transaction_type: str, amount_cents: int, currency: str, status: str
) -> dict:
    now = datetime.now(tz=timezone.utc)
    now_iso = now.isoformat()
    transaction_id = uuid.uuid4().hex
    sort_key = now.strftime("%Y%m%dT%H%M%S%f")
    item = {
        "id": transaction_id,
        "account_id": account_id,
        "type": transaction_type,
        "amount_cents": amount_cents,
        "currency": currency,
        "status": status,
        "created_at": now_iso,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(account_id),
            "SK": _transaction_sk(sort_key, transaction_id),
            "entityType": "Transaction",
            **item,
        }
    )
    return item


def list_transactions(account_id: str) -> list[dict]:
    table = get_table()
    items: list[dict] = []
    query_kwargs: dict = {
        "KeyConditionExpression": Key("PK").eq(_pk(account_id)) & Key("SK").begins_with("TRANSACTION#"),
        "ScanIndexForward": False,
    }
    while True:
        resp = table.query(**query_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key
    return [_strip(item) for item in items]


# ---- Admin listings (catalog §15) ------------------------------------------


def list_all_subscriptions() -> list[dict]:
    """Table scan across every account's subscription item. Same documented
    "dev/test scale" tradeoff as `profiles_repo.list_all_profiles`.
    """
    from boto3.dynamodb.conditions import Attr

    table = get_table()
    items: list[dict] = []
    scan_kwargs: dict = {"FilterExpression": Attr("entityType").eq("Subscription")}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return [_strip(item) for item in items]


def list_all_transactions() -> list[dict]:
    """Table scan across every account's transaction rows."""
    from boto3.dynamodb.conditions import Attr

    table = get_table()
    items: list[dict] = []
    scan_kwargs: dict = {"FilterExpression": Attr("entityType").eq("Transaction")}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return [_strip(item) for item in items]
