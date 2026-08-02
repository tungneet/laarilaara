"""Profile managers, manager-invitations, and candidate-consent (catalog §5).

Permission model recap: every manager row has ``role`` (``owner`` |
``candidate`` | ``parent`` | ``collaborator``) and a ``permissions`` list.
Only ``profile.manage_managers`` lets an account invite/patch/revoke other
managers; only the profile owner (created via ``POST /v1/profiles``) has it
today, since the invite/accept flow is what grants it to anyone else.

Known simplifications (flagged for later): invited "candidate" role is only
meaningful for ``relationship=other`` profiles (a parent inviting the actual
candidate to co-manage/consent for themselves); nothing currently prevents
inviting a second "owner"-equivalent manager with full permissions if the
inviter chooses to grant ``profile.manage_managers`` in the invitation, which
is intentional (lets an owner delegate full control) but worth a security
review once real abuse cases are considered.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.domain.profiles import ProfileRelationship
from app.repositories import accounts as accounts_repo
from app.repositories import profile_candidate_consents as candidate_consents_repo
from app.repositories import profile_manager_invitations as invitations_repo
from app.repositories import profile_managers as managers_repo
from app.services import profiles as profiles_service
from app.services.notifications import send_manager_invitation

ALLOWED_INVITE_PERMISSIONS = {
    "profile.read_private",
    "profile.edit",
    "profile.publish",
    "profile.manage_managers",
}


class InvitationNotFoundError(Exception):
    pass


class InvitationNotPendingError(Exception):
    pass


class InvitationEmailMismatchError(Exception):
    pass


class ManagerNotFoundError(Exception):
    pass


class CannotOrphanProfileError(Exception):
    pass


class CannotRevokeCandidateManagerError(Exception):
    pass


class CandidateConsentForbiddenError(Exception):
    """Caller is not the verified candidate for this profile."""


def _mask_invitation(item: dict) -> dict:
    return {
        "id": item["id"],
        "role": item["role"],
        "permissions": item["permissions"],
        "status": item["status"],
        "invited_email": _mask_email(item["invitedEmail"]),
        "created_at": item["createdAt"],
        "expires_at": item["expiresAt"],
    }


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not local:
        return email
    return f"{local[0]}***@{domain}"


def _to_manager_view(item: dict) -> dict:
    return {
        "account_id": item["accountId"],
        "role": item["role"],
        "permissions": item["permissions"],
        "is_primary": item["isPrimary"],
        "created_at": item["createdAt"],
    }


def list_managers(account_id: str, profile_id: str) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.read_private")
    managers = managers_repo.list_managers(profile_id)
    invitations = [
        item for item in invitations_repo.list_invitations(profile_id) if item["status"] == "pending"
    ]
    return {
        "managers": [_to_manager_view(item) for item in managers],
        "pending_invitations": [_mask_invitation(item) for item in invitations],
    }


def invite_manager(
    account_id: str,
    profile_id: str,
    invited_email: str,
    role: str,
    permissions: list[str],
) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.manage_managers")
    profiles_service.get_or_404(profile_id)

    safe_permissions = [p for p in permissions if p in ALLOWED_INVITE_PERMISSIONS]
    item, token = invitations_repo.create_invitation(
        profile_id, account_id, invited_email, role, safe_permissions
    )
    send_manager_invitation(invited_email, token, item["id"])
    return _mask_invitation(item)


def accept_invitation(token: str, accepting_account_id: str) -> dict:
    item = invitations_repo.get_invitation_by_token(token)
    if item is None:
        raise InvitationNotFoundError(token)

    if item["status"] != "pending" or datetime.fromisoformat(item["expiresAt"]) <= datetime.now(
        tz=timezone.utc
    ):
        raise InvitationNotPendingError(item["id"])

    account = accounts_repo.get_account_by_id(accepting_account_id)
    if account is None or item["invitedEmail"].strip().lower() != account.email.strip().lower():
        raise InvitationEmailMismatchError(item["id"])

    invitations_repo.mark_accepted(item["profileId"], item["id"], accepting_account_id)
    manager = managers_repo.create_manager(
        item["profileId"],
        accepting_account_id,
        role=item["role"],
        permissions=item["permissions"],
        is_primary=False,
    )
    return _to_manager_view(manager)


def update_manager(
    account_id: str,
    profile_id: str,
    target_account_id: str,
    *,
    permissions: list[str] | None,
    is_primary: bool | None,
) -> dict:
    profiles_service.require_permission(profile_id, account_id, "profile.manage_managers")

    if is_primary:
        for other in managers_repo.list_managers(profile_id):
            if other["accountId"] != target_account_id and other.get("isPrimary"):
                managers_repo.unset_primary(profile_id, other["accountId"])

    safe_permissions = (
        [p for p in permissions if p in ALLOWED_INVITE_PERMISSIONS]
        if permissions is not None
        else None
    )
    try:
        manager = managers_repo.update_manager(
            profile_id,
            target_account_id,
            permissions=safe_permissions,
            is_primary=is_primary,
        )
    except managers_repo.ManagerNotFoundError as exc:
        raise ManagerNotFoundError(target_account_id) from exc
    return _to_manager_view(manager)


def revoke_manager(account_id: str, profile_id: str, target_account_id: str) -> None:
    profiles_service.require_permission(profile_id, account_id, "profile.manage_managers")

    target = managers_repo.get_manager(profile_id, target_account_id)
    if target is None:
        raise ManagerNotFoundError(target_account_id)
    if target["role"] == "candidate":
        raise CannotRevokeCandidateManagerError(target_account_id)

    all_managers = managers_repo.list_managers(profile_id)
    if len(all_managers) <= 1:
        raise CannotOrphanProfileError(profile_id)

    try:
        managers_repo.delete_manager(profile_id, target_account_id)
    except managers_repo.ManagerNotFoundError as exc:
        raise ManagerNotFoundError(target_account_id) from exc


def record_candidate_consent(
    account_id: str, profile_id: str, decision: str, granted: bool
) -> dict:
    profile = profiles_service.get_or_404(profile_id)
    manager = managers_repo.get_manager(profile_id, account_id)
    if manager is None:
        raise profiles_service.ProfileNotFoundError(profile_id)

    is_candidate = (
        profile.relationship is ProfileRelationship.SELF and manager["role"] == "owner"
    ) or manager["role"] == "candidate"
    if not is_candidate:
        raise CandidateConsentForbiddenError(account_id)

    item = candidate_consents_repo.record_candidate_consent(
        profile_id, account_id, decision, granted
    )
    return {
        "profile_id": item["profileId"],
        "decision": item["decision"],
        "granted": item["granted"],
        "decided_at": item["decidedAt"],
    }
