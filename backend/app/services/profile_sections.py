"""Single-resource profile sections service (catalog §5 — "Sections" batch:
personal-details, narratives, lifestyle, visibility).

All four sections share the same shape (one current resource, GET requires
``profile.read_private``, PATCH requires ``profile.edit`` and merges only the
fields supplied). PATCH bumps the profile aggregate's ``version`` via
``profiles_repo.touch_version`` since these are all "compatibility/discovery
input" fields per the catalog's blanket rule for §5 writes.

Known simplification (documented for later): the catalog also calls for
writes to "append a safe revision" and "write an outbox row" (published to
EventBridge). Neither a revision-history store nor the outbox/dispatcher
infrastructure exists yet anywhere in this codebase, so both are deferred
until that infrastructure is built; only the version bump is implemented for
now.

Narratives text (headline/bio/partner_expectations/family_narrative) is run
through the central `app.core.ai_engine`'s `enforce_moderation` (Block 14)
before being saved, and the PATCH is rejected (`NarrativeContentBlockedError`)
if flagged content is at/above the configured block threshold.
"""
from __future__ import annotations

from app.core import ai_engine
from app.repositories import profile_sections as sections_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service

_PERSONAL_DETAILS = "PERSONAL_DETAILS"
_NARRATIVES = "NARRATIVES"
_LIFESTYLE = "LIFESTYLE"
_VISIBILITY = "VISIBILITY"

_MODERATED_NARRATIVE_FIELDS = ("headline", "bio", "partner_expectations", "family_narrative")


class NarrativeContentBlockedError(Exception):
    """Raised when `app.core.ai_engine.enforce_moderation` flags a narrative
    field at/above the configured block threshold."""

    def __init__(self, field_name: str, moderation: ai_engine.ModerationResult) -> None:
        super().__init__(f"content blocked for field: {field_name}")
        self.field_name = field_name
        self.moderation = moderation


def _get(account_id: str, profile_id: str, section: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sections_repo.get_section(profile_id, section)


def _patch(account_id: str, profile_id: str, section: str, updates: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    merged = sections_repo.patch_section(profile_id, section, updates)
    profiles_repo.touch_version(profile_id)
    return merged


def get_personal_details(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _PERSONAL_DETAILS)


def patch_personal_details(account_id: str, profile_id: str, updates: dict) -> dict:
    return _patch(account_id, profile_id, _PERSONAL_DETAILS, updates)


def get_narratives(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _NARRATIVES)


def patch_narratives(account_id: str, profile_id: str, updates: dict) -> dict:
    for field_name in _MODERATED_NARRATIVE_FIELDS:
        text = updates.get(field_name)
        try:
            ai_engine.enforce_moderation(text)
        except ai_engine.ContentBlockedError as exc:
            raise NarrativeContentBlockedError(field_name, exc.moderation) from exc
    return _patch(account_id, profile_id, _NARRATIVES, updates)


def get_lifestyle(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _LIFESTYLE)


def patch_lifestyle(account_id: str, profile_id: str, updates: dict) -> dict:
    return _patch(account_id, profile_id, _LIFESTYLE, updates)


def get_visibility(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _VISIBILITY)


def patch_visibility(account_id: str, profile_id: str, updates: dict) -> dict:
    return _patch(account_id, profile_id, _VISIBILITY, updates)
