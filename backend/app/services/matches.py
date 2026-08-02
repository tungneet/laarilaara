"""Matches service (catalog §8: `GET /v1/matches`, `GET /v1/matches/{matchId}`,
`POST /v1/matches/{matchId}/end`, `POST /v1/matches/{matchId}/feedback`,
`POST /v1/matches/{matchId}/outcomes`).

``conversation_id`` is populated as soon as the accompanying interest is
accepted (see `app.services.interests.accept_interest`, catalog §9
messaging).
"""
from __future__ import annotations

from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.repositories import matches as matches_repo
from app.services import profiles as profiles_service

_VALID_OUTCOMES = {"engaged", "married", "ended_amicably", "other"}


class MatchNotFoundError(Exception):
    pass


class MatchStateConflictError(Exception):
    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"expected status {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class OutcomeConsentRequiredError(Exception):
    pass


def _get_or_404(match_id: str) -> dict:
    match = matches_repo.get_match(match_id)
    if match is None:
        raise MatchNotFoundError(match_id)
    return match


def _require_participant(acting_profile_id: str, match: dict) -> None:
    if acting_profile_id not in (match["profile_a_id"], match["profile_b_id"]):
        # Mask existence: a non-participant sees the same 404 as a missing match.
        raise MatchNotFoundError(match["id"])


def list_matches(
    account_id: str, acting_profile_id: str, status: str | None, cursor: str | None, limit: int
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    items = matches_repo.list_for_profile(acting_profile_id, status)
    offset = _decode_cursor(cursor)
    page = items[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(items) else None
    return {"items": page, "next_cursor": next_cursor}


def get_match(account_id: str, acting_profile_id: str, match_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    match = _get_or_404(match_id)
    _require_participant(acting_profile_id, match)
    return match


def end_match(account_id: str, acting_profile_id: str, match_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    match = _get_or_404(match_id)
    _require_participant(acting_profile_id, match)
    if match["status"] == "ended":
        return match
    return matches_repo.end_match(match_id)


def submit_feedback(
    account_id: str, acting_profile_id: str, match_id: str, rating: int, comment: str | None
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    match = _get_or_404(match_id)
    _require_participant(acting_profile_id, match)
    return matches_repo.put_feedback(match_id, acting_profile_id, {"rating": rating, "comment": comment})


def submit_outcome(
    account_id: str, acting_profile_id: str, match_id: str, outcome: str, consent: bool
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    match = _get_or_404(match_id)
    _require_participant(acting_profile_id, match)
    if not consent:
        raise OutcomeConsentRequiredError(match_id)
    return matches_repo.put_outcome(match_id, acting_profile_id, {"outcome": outcome, "consent": consent})
