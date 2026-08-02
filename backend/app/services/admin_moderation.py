"""Admin moderation-case service (catalog §15 "Moderation").

Cases wrap `moderation_cases.py`; posting a case action creates a real
`ModerationAction` row via `moderation_actions_repo.create_action` (catalog
§11) — the first real consequence for the "queued forever" `reports`
resource that class of gap describes.
"""
from __future__ import annotations

from app.repositories import admin_audit as admin_audit_repo
from app.repositories import moderation_actions as moderation_actions_repo
from app.repositories import moderation_cases as moderation_cases_repo


class ModerationCaseNotFoundError(Exception):
    pass


class ModerationCaseAlreadyClosedError(Exception):
    pass


def list_cases(status_filter: str | None) -> list[dict]:
    return moderation_cases_repo.list_cases(status_filter)


def get_case(case_id: str) -> dict:
    case = moderation_cases_repo.get_case(case_id)
    if case is None:
        raise ModerationCaseNotFoundError(case_id)
    return case


def assign_case(admin_account_id: str, case_id: str, reason: str) -> dict:
    case = get_case(case_id)
    if case["status"] == "closed":
        raise ModerationCaseAlreadyClosedError(case_id)
    updated = moderation_cases_repo.assign_case(case_id, admin_account_id)
    admin_audit_repo.record(admin_account_id, "moderation.case.assign", "moderation_case", case_id, reason)
    return updated


def act_on_case(admin_account_id: str, case_id: str, action_type: str, reason: str) -> dict:
    case = get_case(case_id)
    if case["status"] == "closed":
        raise ModerationCaseAlreadyClosedError(case_id)
    action = moderation_actions_repo.create_action(case["subject_account_id"], action_type, reason)
    admin_audit_repo.record(admin_account_id, "moderation.case.action", "moderation_case", case_id, reason)
    return action


def close_case(admin_account_id: str, case_id: str, reason: str) -> dict:
    case = get_case(case_id)
    if case["status"] == "closed":
        raise ModerationCaseAlreadyClosedError(case_id)
    updated = moderation_cases_repo.close_case(case_id)
    admin_audit_repo.record(admin_account_id, "moderation.case.close", "moderation_case", case_id, reason)
    return updated
