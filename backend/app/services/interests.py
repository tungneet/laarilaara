"""Interests service (catalog §8: `GET/POST /v1/interests`,
`POST /v1/interests/{interestId}/accept|decline|withdraw`).

State machine: ``pending`` -> ``accepted`` | ``declined`` | ``withdrawn``.
Accepting atomically creates a `Match` (see `app.services.matches`).

KNOWN GAPS (documented, no existing infra to build on):
- No entitlement/rate-limit checks exist yet (catalog: "entitlement/rate/block
  checks") — `entitlements.py` is a freemium/premium seam only, and there is
  no block/report system anywhere in this codebase (same gap already flagged
  in §7 discovery's shortlist/hidden-profiles).
- "Optional approved introduction" text accompanying an interest is modeled
  simply as `message`; there is no separate introduction-approval workflow.
"""
from __future__ import annotations

from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.repositories import conversations as conversations_repo
from app.repositories import interests as interests_repo
from app.repositories import matches as matches_repo
from app.services import profiles as profiles_service

_TERMINAL_STATUSES = {"accepted", "declined", "withdrawn"}


class InterestNotFoundError(Exception):
    pass


class InterestStateConflictError(Exception):
    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"expected status {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class InterestSelfTargetError(Exception):
    pass


def _get_or_404(interest_id: str) -> dict:
    interest = interests_repo.get_interest(interest_id)
    if interest is None:
        raise InterestNotFoundError(interest_id)
    return interest


def send_interest(
    account_id: str, acting_profile_id: str, target_profile_id: str, message: str | None
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)
    profiles_service.get_or_404(target_profile_id)
    if acting_profile_id == target_profile_id:
        raise InterestSelfTargetError(acting_profile_id)

    existing = interests_repo.find_pending(acting_profile_id, target_profile_id)
    if existing is not None:
        return existing
    return interests_repo.create_interest(acting_profile_id, target_profile_id, message)


def list_interests(
    account_id: str,
    acting_profile_id: str,
    direction: str,
    status: str | None,
    cursor: str | None,
    limit: int,
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    items = interests_repo.list_for_profile(acting_profile_id, direction, status)
    offset = _decode_cursor(cursor)
    page = items[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(items) else None
    return {"items": page, "next_cursor": next_cursor}


def accept_interest(account_id: str, acting_profile_id: str, interest_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    interest = _get_or_404(interest_id)
    if interest["to_profile_id"] != acting_profile_id:
        # Mask existence: only the recipient may act on this interest.
        raise InterestNotFoundError(interest_id)
    if interest["status"] != "pending":
        raise InterestStateConflictError("pending", interest["status"])

    updated = interests_repo.update_status(interest_id, "accepted")
    match = matches_repo.create_match(interest_id, interest["from_profile_id"], interest["to_profile_id"])
    conversation = conversations_repo.create_conversation(
        match["id"], match["profile_a_id"], match["profile_b_id"]
    )
    matches_repo.set_conversation_id(match["id"], conversation["id"])
    return {**updated, "match_id": match["id"]}


def decline_interest(
    account_id: str, acting_profile_id: str, interest_id: str, reason: str | None
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    interest = _get_or_404(interest_id)
    if interest["to_profile_id"] != acting_profile_id:
        raise InterestNotFoundError(interest_id)
    if interest["status"] == "declined":
        return interest
    if interest["status"] != "pending":
        raise InterestStateConflictError("pending", interest["status"])

    return interests_repo.update_status(interest_id, "declined", decline_reason=reason)


def withdraw_interest(account_id: str, acting_profile_id: str, interest_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    interest = _get_or_404(interest_id)
    if interest["from_profile_id"] != acting_profile_id:
        raise InterestNotFoundError(interest_id)
    if interest["status"] == "withdrawn":
        return interest
    if interest["status"] != "pending":
        raise InterestStateConflictError("pending", interest["status"])

    return interests_repo.update_status(interest_id, "withdrawn")
