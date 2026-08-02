"""Admin generic reference-data service (catalog §15 "Reference data").

Deactivate-not-delete lifecycle per catalog ("never hard-delete used
options") — there is deliberately no delete function anywhere in this
stack for reference-data items.
"""
from __future__ import annotations

from app.repositories import admin_audit as admin_audit_repo
from app.repositories import reference_data_admin as reference_data_repo


class ReferenceDataItemNotFoundError(Exception):
    pass


class ReferenceDataItemAlreadyExistsError(Exception):
    pass


def list_items(list_name: str, include_inactive: bool) -> list[dict]:
    return reference_data_repo.list_items(list_name, include_inactive)


def create_item(admin_account_id: str, list_name: str, item_id: str, label: str, value: dict | None, reason: str) -> dict:
    try:
        item = reference_data_repo.create_item(list_name, item_id, label, value)
    except reference_data_repo.ReferenceDataItemAlreadyExistsError as exc:
        raise ReferenceDataItemAlreadyExistsError(item_id) from exc
    admin_audit_repo.record(admin_account_id, "reference.item.create", list_name, item_id, reason)
    return item


def update_item(
    admin_account_id: str, list_name: str, item_id: str, label: str | None, value: dict | None, reason: str
) -> dict:
    updated = reference_data_repo.update_item(list_name, item_id, label, value)
    if updated is None:
        raise ReferenceDataItemNotFoundError(item_id)
    admin_audit_repo.record(admin_account_id, "reference.item.update", list_name, item_id, reason)
    return updated


def deactivate_item(admin_account_id: str, list_name: str, item_id: str, reason: str) -> dict:
    updated = reference_data_repo.deactivate_item(list_name, item_id)
    if updated is None:
        raise ReferenceDataItemNotFoundError(item_id)
    admin_audit_repo.record(admin_account_id, "reference.item.deactivate", list_name, item_id, reason)
    return updated
