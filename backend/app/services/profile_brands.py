"""Brands and experiences service (catalog §5 — "Sections" batch F:
`GET/PUT .../brands`, `GET/PUT .../experiences`).

Both are replace-set resources reusing the existing `profile_sets.py`
generic repo as-is. Unlike the batch B sets (communities/religious-practices/
languages/interests) there is no seeded controlled-option list for brand or
experience ids yet — the admin `GET/PATCH /v1/admin/brands/{id}` and
`/v1/admin/experiences/{id}` endpoints (and their backing storage) do not
exist in this codebase yet. Known simplification: values are validated for
format only (non-empty, max 64 chars) rather than membership in an
authoritative brand/experience catalog; tighten this once admin brand/
experience management is built.
"""
from __future__ import annotations

from app.repositories import profile_sets as sets_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service
from app.services.profile_sets import InvalidSetValueError

_BRANDS = "BRANDS"
_EXPERIENCES = "EXPERIENCES"

_MAX_VALUE_LENGTH = 64


def _validate_format(values: list[str]) -> None:
    invalid = [v for v in values if not v or len(v) > _MAX_VALUE_LENGTH]
    if invalid:
        raise InvalidSetValueError(invalid)


def get_brands(account_id: str, profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sets_repo.get_set(profile_id, _BRANDS)


def put_brands(account_id: str, profile_id: str, values: list[str]) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    _validate_format(values)
    result = sets_repo.replace_set(profile_id, _BRANDS, values)
    profiles_repo.touch_version(profile_id)
    return result


def get_experiences(account_id: str, profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sets_repo.get_set(profile_id, _EXPERIENCES)


def put_experiences(account_id: str, profile_id: str, values: list[str]) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    _validate_format(values)
    result = sets_repo.replace_set(profile_id, _EXPERIENCES, values)
    profiles_repo.touch_version(profile_id)
    return result
