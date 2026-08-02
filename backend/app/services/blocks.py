"""Blocks service (catalog §11: `GET/PUT/DELETE /v1/blocks/{targetProfileId}`).

Reuses the `profile_target_links.py` generic keyed-link repo (kind
``BLOCK``), same pattern as shortlist/hidden-profiles.

KNOWN GAP: the catalog says a block "suppresses both-way interaction
without notifying target" — that enforcement is NOT yet wired into
discovery/interests/conversations (this batch only builds the block
resource itself, a cross-cutting enforcement pass across those services is
still needed, same class of gap previously flagged for §7/§8/§9 before this
resource existed).
"""
from __future__ import annotations

from app.repositories import profile_target_links as links_repo
from app.services import profiles as profiles_service

_KIND = "BLOCK"


def list_blocks(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    return links_repo.list_links(profile_id, _KIND)


def block_profile(account_id: str, profile_id: str, target_profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    profiles_service.get_or_404(target_profile_id)
    return links_repo.put_link(profile_id, _KIND, target_profile_id, {})


def unblock_profile(account_id: str, profile_id: str, target_profile_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    links_repo.delete_link(profile_id, _KIND, target_profile_id)
