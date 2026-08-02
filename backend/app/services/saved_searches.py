"""Saved-search service (catalog §7: `GET/POST /v1/saved-searches`,
`PATCH/DELETE /v1/saved-searches/{searchId}`).

Reuses the existing `profile_records.py` generic list/CRUD-record repo as-is
(kind=``SAVEDSEARCH``) — no repo changes needed. POST is idempotent by
reusing an existing saved search with the same ``name`` for the acting
profile, mirroring `contacts.py`'s "re-adding the same value reuses the
existing record" convention.
"""
from __future__ import annotations

from app.repositories import profile_records as records_repo
from app.services import profiles as profiles_service

_KIND = "SAVEDSEARCH"


class SavedSearchNotFoundError(Exception):
    pass


def list_saved_searches(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return records_repo.list_records(profile_id, _KIND)


def create_saved_search(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)

    existing = [r for r in records_repo.list_records(profile_id, _KIND) if r["name"] == fields["name"]]
    if existing:
        return existing[0]
    return records_repo.create_record(profile_id, _KIND, fields)


def patch_saved_search(account_id: str, profile_id: str, search_id: str, updates: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        return records_repo.update_record(profile_id, _KIND, search_id, updates)
    except records_repo.RecordNotFoundError as exc:
        raise SavedSearchNotFoundError(search_id) from exc


def delete_saved_search(account_id: str, profile_id: str, search_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        records_repo.delete_record(profile_id, _KIND, search_id)
    except records_repo.RecordNotFoundError as exc:
        raise SavedSearchNotFoundError(search_id) from exc
