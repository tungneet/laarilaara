"""Admin verification-decision service (catalog §15 "Verification").

`decide_request` is the first place anywhere in the codebase a
`VerificationRequest` transitions past ``submitted`` (see
`app.repositories.verification_requests` and `app.services.verification`).
"""
from __future__ import annotations

from app.repositories import admin_audit as admin_audit_repo
from app.repositories import verification_requests as verification_requests_repo


class VerificationRequestNotFoundError(Exception):
    pass


class VerificationRequestNotSubmittedError(Exception):
    pass


def list_requests(status_filter: str | None) -> list[dict]:
    return verification_requests_repo.list_all_requests(status_filter)


def decide(admin_account_id: str, request_id: str, decision: str, reason: str) -> dict:
    request = verification_requests_repo.get_request(request_id)
    if request is None:
        raise VerificationRequestNotFoundError(request_id)
    if request["status"] != "submitted":
        raise VerificationRequestNotSubmittedError(request_id)
    updated = verification_requests_repo.decide_request(request_id, decision, reason)
    admin_audit_repo.record(
        admin_account_id, f"verification.request.{decision}", "verification_request", request_id, reason
    )
    return updated
