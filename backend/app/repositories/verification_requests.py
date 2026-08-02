"""Verification request repository (catalog §11: verification-requests
create/get/evidence/submit, and the derived verification-claims read).

Item shape:  PK = ``VERIFICATIONREQUEST#{id}``   SK = ``VERIFICATIONREQUEST``

State machine: ``draft`` (created, evidence may be attached) ->
``submitted`` (locked, evidence complete) -> ``approved``/``rejected`` via
the catalog §15 admin decision endpoint (`decide_request`, called from
`app.services.admin_verification`). Before that admin endpoint existed,
requests stayed ``submitted`` forever — same class of "no worker/reviewer"
gap as `ai_artifacts.py`/`data_requests.py`/`reports.py`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(request_id: str) -> str:
    return f"VERIFICATIONREQUEST#{request_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_request(profile_id: str, check_type: str) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    item = {
        "PK": _pk(request_id),
        "SK": "VERIFICATIONREQUEST",
        "entityType": "VerificationRequest",
        "id": request_id,
        "profile_id": profile_id,
        "check_type": check_type,
        "status": "draft",
        "evidence_asset_ids": [],
        "created_at": now,
        "submitted_at": None,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_request(request_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(request_id), "SK": "VERIFICATIONREQUEST"})
    item = resp.get("Item")
    return _strip(item) if item else None


def find_open_request(profile_id: str, check_type: str) -> dict | None:
    """Idempotency helper: reuse an existing non-terminal request for the
    same (profile, check_type) instead of creating a duplicate. No GSI/query
    support needed at this size — a table scan filtered in Python mirrors
    the same "small dev/test scale" tradeoff already documented elsewhere
    (e.g. `profiles_repo.list_published_profiles`).
    """
    table = get_table()
    resp = table.scan()
    for item in resp.get("Items", []):
        if (
            item.get("entityType") == "VerificationRequest"
            and item.get("profile_id") == profile_id
            and item.get("check_type") == check_type
            and item.get("status") in ("draft", "submitted")
        ):
            return _strip(item)
    return None


def add_evidence(request_id: str, asset_id: str) -> dict:
    request = get_request(request_id)
    if request is None:
        raise ValueError(request_id)
    evidence_ids = list(request.get("evidence_asset_ids") or [])
    if asset_id not in evidence_ids:
        evidence_ids.append(asset_id)
    table = get_table()
    table.update_item(
        Key={"PK": _pk(request_id), "SK": "VERIFICATIONREQUEST"},
        UpdateExpression="SET evidence_asset_ids = :ids",
        ExpressionAttributeValues={":ids": evidence_ids},
    )
    request["evidence_asset_ids"] = evidence_ids
    return request


def mark_submitted(request_id: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    table = get_table()
    table.update_item(
        Key={"PK": _pk(request_id), "SK": "VERIFICATIONREQUEST"},
        UpdateExpression="SET #status = :status, submitted_at = :submitted_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":status": "submitted", ":submitted_at": now},
    )
    request = get_request(request_id)
    assert request is not None
    return request


def list_all_requests(status_filter: str | None = None) -> list[dict]:
    """Admin listing (catalog §15). Table scan — same documented "dev/test
    scale" tradeoff as `find_open_request`.
    """
    table = get_table()
    resp = table.scan()
    items = []
    for item in resp.get("Items", []):
        if item.get("entityType") != "VerificationRequest":
            continue
        if status_filter and item.get("status") != status_filter:
            continue
        items.append(_strip(item))
    return items


def decide_request(request_id: str, decision: str, reason: str) -> dict:
    """Admin decision (catalog §15): finally transitions a `submitted`
    request to ``approved``/``rejected`` — the first time this state
    machine reaches a terminal state anywhere in the codebase (see module
    docstring).
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    table = get_table()
    table.update_item(
        Key={"PK": _pk(request_id), "SK": "VERIFICATIONREQUEST"},
        UpdateExpression=(
            "SET #status = :status, decided_at = :decided_at, decision_reason = :reason"
        ),
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": decision,
            ":decided_at": now,
            ":reason": reason,
        },
    )
    request = get_request(request_id)
    assert request is not None
    return request
