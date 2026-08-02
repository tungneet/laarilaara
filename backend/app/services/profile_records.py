"""Education and employment records service (catalog §5 — "Sections" batch
C: `education` and `employment`, both list/add + change/remove-one shapes).

``education_level``/``occupation_category`` are validated against the same
controlled option lists that back `/v1/reference/education-levels` and
`/v1/reference/occupation-categories`.
"""
from __future__ import annotations

from app.domain import reference_data
from app.repositories import profile_records as records_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service

_EDUCATION = "EDUCATION"
_EMPLOYMENT = "EMPLOYMENT"

_ALLOWED_EDUCATION_LEVEL_IDS = {item["id"] for item in reference_data.EDUCATION_LEVELS}
_ALLOWED_OCCUPATION_CATEGORY_IDS = {item["id"] for item in reference_data.OCCUPATION_CATEGORIES}


class RecordNotFoundError(Exception):
    pass


class InvalidRecordValueError(Exception):
    def __init__(self, field: str, value: str) -> None:
        super().__init__(f"invalid {field}: {value}")
        self.field = field
        self.value = value


def _require_valid(field: str, value: str | None, allowed: set[str]) -> None:
    if value is not None and value not in allowed:
        raise InvalidRecordValueError(field, value)


def list_education(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return records_repo.list_records(profile_id, _EDUCATION)


def add_education(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    _require_valid(
        "education_level", fields.get("education_level"), _ALLOWED_EDUCATION_LEVEL_IDS
    )
    record = records_repo.create_record(profile_id, _EDUCATION, fields)
    profiles_repo.touch_version(profile_id)
    return record


def get_education_record(account_id: str, profile_id: str, record_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    record = records_repo.get_record(profile_id, _EDUCATION, record_id)
    if record is None:
        raise RecordNotFoundError(record_id)
    return record


def patch_education_record(
    account_id: str, profile_id: str, record_id: str, updates: dict
) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    _require_valid(
        "education_level", updates.get("education_level"), _ALLOWED_EDUCATION_LEVEL_IDS
    )
    try:
        record = records_repo.update_record(profile_id, _EDUCATION, record_id, updates)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(record_id) from exc
    profiles_repo.touch_version(profile_id)
    return record


def delete_education_record(account_id: str, profile_id: str, record_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        records_repo.delete_record(profile_id, _EDUCATION, record_id)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(record_id) from exc
    profiles_repo.touch_version(profile_id)


def list_employment(account_id: str, profile_id: str) -> list[dict]:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    return records_repo.list_records(profile_id, _EMPLOYMENT)


def add_employment(account_id: str, profile_id: str, fields: dict) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    _require_valid(
        "occupation_category",
        fields.get("occupation_category"),
        _ALLOWED_OCCUPATION_CATEGORY_IDS,
    )
    record = records_repo.create_record(profile_id, _EMPLOYMENT, fields)
    profiles_repo.touch_version(profile_id)
    return record


def get_employment_record(account_id: str, profile_id: str, record_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(profile_id)
    record = records_repo.get_record(profile_id, _EMPLOYMENT, record_id)
    if record is None:
        raise RecordNotFoundError(record_id)
    return record


def patch_employment_record(
    account_id: str, profile_id: str, record_id: str, updates: dict
) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    _require_valid(
        "occupation_category",
        updates.get("occupation_category"),
        _ALLOWED_OCCUPATION_CATEGORY_IDS,
    )
    try:
        record = records_repo.update_record(profile_id, _EMPLOYMENT, record_id, updates)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(record_id) from exc
    profiles_repo.touch_version(profile_id)
    return record


def delete_employment_record(account_id: str, profile_id: str, record_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    try:
        records_repo.delete_record(profile_id, _EMPLOYMENT, record_id)
    except records_repo.RecordNotFoundError as exc:
        raise RecordNotFoundError(record_id) from exc
    profiles_repo.touch_version(profile_id)
