"""Shortlist service (catalog §7: `GET /v1/shortlist`,
`PUT/DELETE /v1/shortlist/{targetProfileId}`).

Reuses the new `profile_target_links.py` generic keyed-link repo (kind
``SHORTLIST``).

KNOWN GAP: the catalog says "blocked targets rejected", but no block/report
system exists anywhere in this codebase yet — there is nothing to enforce
against. Revisit once a blocks/reports feature is built.
"""
from __future__ import annotations

from app.repositories import profile_target_links as links_repo
from app.services import profiles as profiles_service

_KIND = "SHORTLIST"


def list_shortlist(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return links_repo.list_links(profile_id, _KIND)


def put_shortlist(account_id: str, profile_id: str, target_profile_id: str, note: str | None) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    profiles_service.get_or_404(target_profile_id)
    return links_repo.put_link(profile_id, _KIND, target_profile_id, {"note": note})


def delete_shortlist(account_id: str, profile_id: str, target_profile_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    links_repo.delete_link(profile_id, _KIND, target_profile_id)
