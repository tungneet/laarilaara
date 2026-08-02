"""Hidden-profiles service (catalog §7:
`PUT/DELETE /v1/hidden-profiles/{targetProfileId}`).

Reuses the `profile_target_links.py` generic keyed-link repo (kind
``HIDDEN``). Hiding a target only removes it from the acting profile's own
discovery search/recommendations (see `app.services.discovery`) — it is a
personal filter, not a global visibility change to the target profile.

KNOWN GAP: the catalog says unhide "cannot override a safety block", but no
safety/block system exists anywhere in this codebase yet — there is nothing
to enforce against. Revisit once that system is built.
"""
from __future__ import annotations

from app.repositories import profile_target_links as links_repo
from app.services import profiles as profiles_service

_KIND = "HIDDEN"


def hide_profile(account_id: str, profile_id: str, target_profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    profiles_service.get_or_404(target_profile_id)
    return links_repo.put_link(profile_id, _KIND, target_profile_id, {})


def unhide_profile(account_id: str, profile_id: str, target_profile_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    links_repo.delete_link(profile_id, _KIND, target_profile_id)
