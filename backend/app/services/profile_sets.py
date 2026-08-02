"""Replace-set profile sections service (catalog §5 — "Sections" batch B:
communities, religious-practices, languages, interests).

All four share the same shape: GET returns the current set, PUT fully
replaces it. Values are validated against the same controlled option lists
that back the public `/v1/reference/*` endpoints (`app/domain/reference_data`),
satisfying the catalog's blanket "validate controlled values" rule for §5
writes without needing a separate admin-managed table yet.
"""
from __future__ import annotations

from app.domain import reference_data
from app.repositories import profile_sets as sets_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service

_COMMUNITIES = "COMMUNITIES"
_RELIGIOUS_PRACTICES = "RELIGIOUS_PRACTICES"
_LANGUAGES = "LANGUAGES"
_INTERESTS = "INTERESTS"

_ALLOWED_COMMUNITY_IDS = {item["id"] for item in reference_data.COMMUNITIES}
_ALLOWED_RELIGIOUS_PRACTICE_IDS = {item["id"] for item in reference_data.RELIGIOUS_PRACTICES}
_ALLOWED_LANGUAGE_CODES = {item["code"] for item in reference_data.LANGUAGES}
_ALLOWED_INTEREST_IDS = {item["id"] for item in reference_data.INTERESTS}


class InvalidSetValueError(Exception):
    def __init__(self, invalid_values: list[str]) -> None:
        super().__init__(f"invalid values: {invalid_values}")
        self.invalid_values = invalid_values


def _get(account_id: str, profile_id: str, name: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sets_repo.get_set(profile_id, name)


def _put(
    account_id: str, profile_id: str, name: str, values: list[str], allowed: set[str]
) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    invalid = [v for v in values if v not in allowed]
    if invalid:
        raise InvalidSetValueError(invalid)
    result = sets_repo.replace_set(profile_id, name, values)
    profiles_repo.touch_version(profile_id)
    return result


def get_communities(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _COMMUNITIES)


def put_communities(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put(account_id, profile_id, _COMMUNITIES, values, _ALLOWED_COMMUNITY_IDS)


def get_religious_practices(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _RELIGIOUS_PRACTICES)


def put_religious_practices(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put(
        account_id, profile_id, _RELIGIOUS_PRACTICES, values, _ALLOWED_RELIGIOUS_PRACTICE_IDS
    )


def get_languages(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _LANGUAGES)


def put_languages(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put(account_id, profile_id, _LANGUAGES, values, _ALLOWED_LANGUAGE_CODES)


def get_interests(account_id: str, profile_id: str) -> dict:
    return _get(account_id, profile_id, _INTERESTS)


def put_interests(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put(account_id, profile_id, _INTERESTS, values, _ALLOWED_INTEREST_IDS)
