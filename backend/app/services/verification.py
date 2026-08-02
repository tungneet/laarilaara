"""Verification + trust-summary service (catalog §11: verification-options,
verification-requests create/get/evidence/submit, verification-claims,
trust-summary).

`_approved_check_types` now reflects real admin decisions (catalog §15
`POST /v1/admin/verification/requests/{id}/decisions`, see
`app.services.admin_verification`): a request only ever reaches
``approved``/``rejected`` via that admin endpoint, so trust_summary/
get_claims stay "unverified" until an admin explicitly approves a request.
"""
from __future__ import annotations

from app.domain.reference_data import VERIFICATION_CHECKS
from app.repositories import media_assets as media_assets_repo
from app.repositories import verification_requests as verification_requests_repo
from app.services import profiles as profiles_service


class VerificationRequestNotFoundError(Exception):
    pass


class VerificationEvidenceAssetNotFoundError(Exception):
    pass


class VerificationRequestAlreadySubmittedError(Exception):
    pass


class VerificationEvidenceRequiredError(Exception):
    pass


def list_options() -> list[dict]:
    return [{"id": c["id"], "label": c["label"]} for c in VERIFICATION_CHECKS]


def trust_summary(account_id: str, acting_profile_id: str, target_profile_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(target_profile_id)
    claims = _approved_check_types(target_profile_id)
    return {
        "profile_id": target_profile_id,
        "trust_label": "verified" if claims else "unverified",
        "verified_checks": claims,
    }


def get_claims(account_id: str, acting_profile_id: str, target_profile_id: str) -> list[dict]:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(target_profile_id)
    return [{"check_type": ct, "status": "submitted"} for ct in _approved_check_types(target_profile_id)]


def _approved_check_types(profile_id: str) -> list[str]:
    requests = verification_requests_repo.list_all_requests(status_filter="approved")
    return [r["check_type"] for r in requests if r["profile_id"] == profile_id]


def create_request(account_id: str, profile_id: str, check_type: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(profile_id)
    existing = verification_requests_repo.find_open_request(profile_id, check_type)
    if existing is not None:
        return existing
    return verification_requests_repo.create_request(profile_id, check_type)


def get_request(account_id: str, acting_profile_id: str, request_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    request = verification_requests_repo.get_request(request_id)
    if request is None or request["profile_id"] != acting_profile_id:
        raise VerificationRequestNotFoundError(request_id)
    return request


def add_evidence(account_id: str, acting_profile_id: str, request_id: str, asset_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    request = get_request(account_id, acting_profile_id, request_id)
    if request["status"] != "draft":
        raise VerificationRequestAlreadySubmittedError(request_id)
    if media_assets_repo.get_asset(asset_id) is None:
        raise VerificationEvidenceAssetNotFoundError(asset_id)
    return verification_requests_repo.add_evidence(request_id, asset_id)


def submit_request(account_id: str, acting_profile_id: str, request_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    request = get_request(account_id, acting_profile_id, request_id)
    if request["status"] == "submitted":
        return request
    if not request["evidence_asset_ids"]:
        raise VerificationEvidenceRequiredError(request_id)
    return verification_requests_repo.mark_submitted(request_id)
