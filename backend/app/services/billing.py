"""Billing service (catalog §13): checkout sessions, subscription
get/cancel/resume, and transaction history.

KNOWN GAP (same class as reports/verification-requests/notifications): no
real payment provider or webhook worker (§14, unbuilt) is wired up here, so:
- Checkout sessions are created with a fake `checkout_url` and never
  transition past ``status="pending"``.
- The subscription record always reflects the account's own ``tier`` field
  (`app/domain/accounts.py`) — since nothing ever upgrades an account to
  ``premium``, `get_subscription` always synthesizes a ``free``/``active``
  subscription on first read if none is stored yet.
- `create_transaction` exists for tests/future-webhook-worker reuse only;
  nothing in the running API creates transaction rows today.
"""
from __future__ import annotations

from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.domain.reference_data import PLANS
from app.repositories import billing as billing_repo


class PlanNotFoundError(Exception):
    pass


def _plan_ids() -> set[str]:
    return {plan["id"] for plan in PLANS}


def create_checkout_session(account_id: str, plan_id: str) -> dict:
    if plan_id not in _plan_ids():
        raise PlanNotFoundError(plan_id)

    existing = billing_repo.find_open_checkout_session(account_id, plan_id)
    if existing is not None:
        return existing

    checkout_url = f"https://billing.example.invalid/checkout/{account_id}/{plan_id}"
    return billing_repo.create_checkout_session(account_id, plan_id, checkout_url)


def get_subscription(account_id: str) -> dict:
    stored = billing_repo.get_subscription(account_id)
    if stored is not None:
        return stored
    return billing_repo.put_subscription(
        account_id, plan_id="free", status="active", cancel_at_period_end=False
    )


def cancel_subscription(account_id: str) -> dict:
    current = get_subscription(account_id)
    return billing_repo.put_subscription(
        account_id,
        plan_id=current["plan_id"],
        status=current["status"],
        cancel_at_period_end=True,
    )


def resume_subscription(account_id: str) -> dict:
    current = get_subscription(account_id)
    return billing_repo.put_subscription(
        account_id,
        plan_id=current["plan_id"],
        status=current["status"],
        cancel_at_period_end=False,
    )


def list_transactions(account_id: str, cursor: str | None, limit: int) -> dict:
    items = billing_repo.list_transactions(account_id)
    offset = _decode_cursor(cursor)
    page = items[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(items) else None
    return {"items": page, "next_cursor": next_cursor}
