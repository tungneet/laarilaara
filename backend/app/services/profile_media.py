"""Profile media attachment service (catalog §6:
`GET/POST /v1/profiles/{profileId}/media`,
`PATCH/DELETE /v1/profiles/{profileId}/media/{profileMediaId}`).

Reuses the existing `profile_records.py` generic list/CRUD-record repo as-is
(kind=``MEDIA``) — no repo changes needed, same pattern as `family/members`.
"""
from __future__ import annotations

from app.repositories import media_assets as media_assets_repo
from app.repositories import profile_records as records_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service

_MEDIA = "MEDIA"


class RecordNotFoundError(Exception):
    pass


class AssetNotReadyError(Exception):
    pass


class AssetNotOwnedError(Exception):
    pass


def list_media(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return records_repo.list_records(profile_id, _MEDIA)


def attach_media(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)

    asset_id = fields["asset_id"]
    asset = media_assets_repo.get_asset(asset_id)
    if asset is None:
        raise RecordNotFoundError(asset_id)
    if asset["account_id"] != account_id:
        raise AssetNotOwnedError(asset_id)
    if asset["status"] != "ready":
        raise AssetNotReadyError(asset_id)

    # Idempotent: reuse an existing attachment of the same asset if present.
    existing = [r for r in records_repo.list_records(profile_id, _MEDIA) if r["asset_id"] == asset_id]
    if existing:
        return existing[0]

    if fields.get("is_primary"):
        _unset_other_primary(profile_id, exclude_record_id=None)

    record = records_repo.create_record(profile_id, _MEDIA, fields)
    profiles_repo.touch_version(profile_id)
    return record


def _unset_other_primary(profile_id: str, exclude_record_id: str | None) -> None:
    for record in records_repo.list_records(profile_id, _MEDIA):
        if record["id"] == exclude_record_id:
            continue
        if record.get("is_primary"):
            records_repo.update_record(profile_id, _MEDIA, record["id"], {"is_primary": False})


def patch_media(account_id: str, profile_id: str, media_id: str, updates: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    if updates.get("is_primary"):
        _unset_other_primary(profile_id, exclude_record_id=media_id)
    try:
        record = records_repo.update_record(profile_id, _MEDIA, media_id, updates)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(media_id) from exc
    profiles_repo.touch_version(profile_id)
    return record


def delete_media(account_id: str, profile_id: str, media_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        records_repo.delete_record(profile_id, _MEDIA, media_id)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(media_id) from exc
    profiles_repo.touch_version(profile_id)
