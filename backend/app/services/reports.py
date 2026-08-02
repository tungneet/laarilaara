"""Reports service (catalog §11: `POST /v1/reports`, `GET /v1/reports/{id}`).

No moderation worker exists anywhere in this codebase yet (same class of
gap as `app.services.ai`/`app.services.data_requests`), so every report is
created with ``status="queued"`` and never transitions further — this is
documented/expected behavior, not a bug, until a moderation review system
exists.

Existence-masking: `get_report` only returns the report to the profile that
filed it (the reporter) — everyone else, including the reported subject,
gets an identical 404, same convention as every other owner-scoped resource
in this codebase.
"""
from __future__ import annotations

from app.repositories import media_assets as media_assets_repo
from app.repositories import reports as reports_repo
from app.services import profiles as profiles_service


class ReportNotFoundError(Exception):
    pass


class ReportEvidenceNotFoundError(Exception):
    pass


def create_report(
    account_id: str,
    reporter_profile_id: str,
    subject_type: str,
    subject_id: str,
    reason: str,
    details: str | None,
    evidence_asset_ids: list[str],
) -> dict:
    profiles_service.require_permission(reporter_profile_id, account_id, "profile.read_private")
    for asset_id in evidence_asset_ids:
        if media_assets_repo.get_asset(asset_id) is None:
            raise ReportEvidenceNotFoundError(asset_id)
    return reports_repo.create_report(
        reporter_profile_id, subject_type, subject_id, reason, details, evidence_asset_ids
    )


def get_report(account_id: str, acting_profile_id: str, report_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    report = reports_repo.get_report(report_id)
    if report is None or report["reporter_profile_id"] != acting_profile_id:
        raise ReportNotFoundError(report_id)
    return report
