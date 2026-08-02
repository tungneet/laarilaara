"""Family section service (catalog §5 — "Sections" batch D): a single-resource
family summary (PUT full-replace, unlike the batch-A sections' PATCH partial
merge) plus a list/CRUD family-members sub-resource reusing the same generic
record repository as education/employment.

Known simplification (documented for later, consistent with the rest of §5
Sections): revision-history append and outbox/EventBridge publishing are
deferred; only the profile aggregate version bump is implemented.
"""
from __future__ import annotations

from app.repositories import profile_records as records_repo
from app.repositories import profile_sections as sections_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service

_FAMILY = "FAMILY"
_FAMILY_MEMBER = "FAMILY_MEMBER"


class RecordNotFoundError(Exception):
    pass


def get_family(account_id: str, profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sections_repo.get_section(profile_id, _FAMILY)


def put_family(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    replaced = sections_repo.replace_section(profile_id, _FAMILY, fields)
    profiles_repo.touch_version(profile_id)
    return replaced


def list_family_members(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return records_repo.list_records(profile_id, _FAMILY_MEMBER)


def add_family_member(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    record = records_repo.create_record(profile_id, _FAMILY_MEMBER, fields)
    profiles_repo.touch_version(profile_id)
    return record


def patch_family_member(
    account_id: str, profile_id: str, member_id: str, updates: dict
) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        record = records_repo.update_record(profile_id, _FAMILY_MEMBER, member_id, updates)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(member_id) from exc
    profiles_repo.touch_version(profile_id)
    return record


def delete_family_member(account_id: str, profile_id: str, member_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        records_repo.delete_record(profile_id, _FAMILY_MEMBER, member_id)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(member_id) from exc
    profiles_repo.touch_version(profile_id)
