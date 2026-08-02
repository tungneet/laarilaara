"""Main partner-preferences service (catalog §5 — "Sections" batch E:
`GET/PUT .../preferences` plus the five preference-set sub-collections
`.../preferences/countries|languages|communities|religious-practices|
education-levels`).

The main preferences resource reuses the existing `profile_sections.py`
single-resource repo with PUT full-replace semantics (same as `family`,
batch D). The five sub-collections reuse the existing `profile_sets.py`
generic replace-set repo as-is (no repo changes needed) and are validated
against the same controlled option lists that back the public
`/v1/reference/*` endpoints (`app/domain/reference_data`) plus
`COUNTRIES`/`LANGUAGES` which also already exist there.
"""
from __future__ import annotations

from app.domain import reference_data
from app.repositories import profile_sections as sections_repo
from app.repositories import profile_sets as sets_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service
from app.services.profile_sets import InvalidSetValueError

_PREFERENCES = "PREFERENCES"
_PREF_COUNTRIES = "PREF_COUNTRIES"
_PREF_LANGUAGES = "PREF_LANGUAGES"
_PREF_COMMUNITIES = "PREF_COMMUNITIES"
_PREF_RELIGIOUS_PRACTICES = "PREF_RELIGIOUS_PRACTICES"
_PREF_EDUCATION_LEVELS = "PREF_EDUCATION_LEVELS"

_ALLOWED_COUNTRY_CODES = {item["code"] for item in reference_data.COUNTRIES}
_ALLOWED_LANGUAGE_CODES = {item["code"] for item in reference_data.LANGUAGES}
_ALLOWED_COMMUNITY_IDS = {item["id"] for item in reference_data.COMMUNITIES}
_ALLOWED_RELIGIOUS_PRACTICE_IDS = {item["id"] for item in reference_data.RELIGIOUS_PRACTICES}
_ALLOWED_EDUCATION_LEVEL_IDS = {item["id"] for item in reference_data.EDUCATION_LEVELS}


def get_preferences(account_id: str, profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sections_repo.get_section(profile_id, _PREFERENCES)


def put_preferences(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    replaced = sections_repo.replace_section(profile_id, _PREFERENCES, fields)
    profiles_repo.touch_version(profile_id)
    return replaced


def _get_set(account_id: str, profile_id: str, name: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return sets_repo.get_set(profile_id, name)


def _put_set(
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


def get_preferred_countries(account_id: str, profile_id: str) -> dict:
    return _get_set(account_id, profile_id, _PREF_COUNTRIES)


def put_preferred_countries(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put_set(account_id, profile_id, _PREF_COUNTRIES, values, _ALLOWED_COUNTRY_CODES)


def get_preferred_languages(account_id: str, profile_id: str) -> dict:
    return _get_set(account_id, profile_id, _PREF_LANGUAGES)


def put_preferred_languages(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put_set(account_id, profile_id, _PREF_LANGUAGES, values, _ALLOWED_LANGUAGE_CODES)


def get_preferred_communities(account_id: str, profile_id: str) -> dict:
    return _get_set(account_id, profile_id, _PREF_COMMUNITIES)


def put_preferred_communities(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put_set(account_id, profile_id, _PREF_COMMUNITIES, values, _ALLOWED_COMMUNITY_IDS)


def get_preferred_religious_practices(account_id: str, profile_id: str) -> dict:
    return _get_set(account_id, profile_id, _PREF_RELIGIOUS_PRACTICES)


def put_preferred_religious_practices(
    account_id: str, profile_id: str, values: list[str]
) -> dict:
    return _put_set(
        account_id,
        profile_id,
        _PREF_RELIGIOUS_PRACTICES,
        values,
        _ALLOWED_RELIGIOUS_PRACTICE_IDS,
    )


def get_preferred_education_levels(account_id: str, profile_id: str) -> dict:
    return _get_set(account_id, profile_id, _PREF_EDUCATION_LEVELS)


def put_preferred_education_levels(account_id: str, profile_id: str, values: list[str]) -> dict:
    return _put_set(
        account_id, profile_id, _PREF_EDUCATION_LEVELS, values, _ALLOWED_EDUCATION_LEVEL_IDS
    )
