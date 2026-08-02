"""Profiles router (catalog §5).

Covers the profile aggregate (create/read/patch, preview, completion,
submit/publish/pause/resume, delete) plus managers, manager-invitations, and
candidate-consent. Sections (personal-details, narratives, etc.) are a later
batch.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.domain.profiles import Profile
from app.schemas.profile import (
    CreateProfileRequest,
    PatchProfileRequest,
    ProfileCompletionResponse,
    ProfilePreviewResponse,
    ProfileResponse,
)
from app.schemas.profile_manager import (
    CandidateConsentRequest,
    CandidateConsentResponse,
    InviteManagerRequest,
    ManagerResponse,
    ManagersListResponse,
    PatchManagerRequest,
    PendingInvitationResponse,
)
from app.services import profile_managers as profile_managers_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])
invitations_router = APIRouter(prefix="/v1/profile-manager-invitations", tags=["profiles"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_NOT_FOUND",
    title="Profile not found",
)

_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to perform this action on this profile",
)


def _to_response(profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        relationship=profile.relationship.value,
        status=profile.status.value,
        version=profile.version,
        locale=profile.locale,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        submitted_at=profile.submitted_at,
        published_at=profile.published_at,
        paused_at=profile.paused_at,
    )


def _state_conflict_error(exc: profiles_service.ProfileStateConflictError) -> ApiError:
    return ApiError(
        status=status.HTTP_409_CONFLICT,
        code="PROFILE_INVALID_STATE",
        title="Profile is not in a state that allows this action",
        detail=f"Expected status '{exc.expected}', but profile is '{exc.actual}'.",
    )


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: CreateProfileRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    profile = profiles_service.create_profile(
        current.account_id, payload.relationship.value, payload.locale
    )
    return _to_response(profile)


@router.get("/{profile_id}", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def get_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.get_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return _to_response(profile)


@router.patch("/{profile_id}", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def patch_profile(
    profile_id: str,
    payload: PatchProfileRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.patch_profile(
            current.account_id, profile_id, payload.locale
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return _to_response(profile)


@router.get(
    "/{profile_id}/preview",
    response_model=ProfilePreviewResponse,
    status_code=status.HTTP_200_OK,
)
async def preview_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfilePreviewResponse:
    try:
        data = profiles_service.preview_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfilePreviewResponse(**data)


@router.get(
    "/{profile_id}/completion",
    response_model=ProfileCompletionResponse,
    status_code=status.HTTP_200_OK,
)
async def get_completion(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileCompletionResponse:
    try:
        data = profiles_service.get_completion(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ProfileCompletionResponse(**data)


@router.post(
    "/{profile_id}/submit", response_model=ProfileResponse, status_code=status.HTTP_200_OK
)
async def submit_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.submit_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profiles_service.ProfileStateConflictError as exc:
        raise _state_conflict_error(exc) from exc
    return _to_response(profile)


@router.post(
    "/{profile_id}/publish", response_model=ProfileResponse, status_code=status.HTTP_200_OK
)
async def publish_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.publish_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profiles_service.ProfileStateConflictError as exc:
        raise _state_conflict_error(exc) from exc
    return _to_response(profile)


@router.post(
    "/{profile_id}/pause", response_model=ProfileResponse, status_code=status.HTTP_200_OK
)
async def pause_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.pause_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profiles_service.ProfileStateConflictError as exc:
        raise _state_conflict_error(exc) from exc
    return _to_response(profile)


@router.post(
    "/{profile_id}/resume", response_model=ProfileResponse, status_code=status.HTTP_200_OK
)
async def resume_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.resume_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profiles_service.ProfileStateConflictError as exc:
        raise _state_conflict_error(exc) from exc
    return _to_response(profile)


@router.delete(
    "/{profile_id}", response_model=ProfileResponse, status_code=status.HTTP_202_ACCEPTED
)
async def delete_profile(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileResponse:
    try:
        profile = profiles_service.delete_profile(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return _to_response(profile)


# ---------------------------------------------------------------------------
# Managers and consent (catalog §5 — "Managers and consent" block)
# ---------------------------------------------------------------------------

_MANAGER_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_MANAGER_NOT_FOUND",
    title="Manager not found",
)

_INVITATION_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_INVITATION_NOT_FOUND",
    title="Invitation not found",
)

_INVITATION_NOT_PENDING_ERROR = ApiError(
    status=status.HTTP_400_BAD_REQUEST,
    code="PROFILE_INVITATION_NOT_PENDING",
    title="Invitation is no longer pending",
)

_INVITATION_EMAIL_MISMATCH_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_INVITATION_EMAIL_MISMATCH",
    title="Authenticated account does not match the invited email",
)

_CANNOT_ORPHAN_PROFILE_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="PROFILE_CANNOT_ORPHAN",
    title="Cannot remove the last manager from a profile",
)

_CANNOT_REVOKE_CANDIDATE_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="PROFILE_CANNOT_REVOKE_CANDIDATE",
    title="Cannot revoke the candidate's own management access",
)

_CANDIDATE_CONSENT_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_CANDIDATE_CONSENT_FORBIDDEN",
    title="Only the verified candidate can record this consent",
)


@router.get(
    "/{profile_id}/managers",
    response_model=ManagersListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_managers(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> ManagersListResponse:
    try:
        data = profile_managers_service.list_managers(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ManagersListResponse(
        managers=[ManagerResponse(**m) for m in data["managers"]],
        pending_invitations=[
            PendingInvitationResponse(**inv) for inv in data["pending_invitations"]
        ],
    )


@router.post(
    "/{profile_id}/manager-invitations",
    response_model=PendingInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_manager(
    profile_id: str,
    payload: InviteManagerRequest,
    current: CurrentSession = Depends(get_current_session),
) -> PendingInvitationResponse:
    try:
        data = profile_managers_service.invite_manager(
            current.account_id,
            profile_id,
            payload.invited_email,
            payload.role,
            payload.permissions,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return PendingInvitationResponse(**data)


@router.patch(
    "/{profile_id}/managers/{account_id}",
    response_model=ManagerResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_manager(
    profile_id: str,
    account_id: str,
    payload: PatchManagerRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ManagerResponse:
    try:
        data = profile_managers_service.update_manager(
            current.account_id,
            profile_id,
            account_id,
            permissions=payload.permissions,
            is_primary=payload.is_primary,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_managers_service.ManagerNotFoundError as exc:
        raise _MANAGER_NOT_FOUND_ERROR from exc
    return ManagerResponse(**data)


@router.delete(
    "/{profile_id}/managers/{account_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_manager(
    profile_id: str,
    account_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        profile_managers_service.revoke_manager(current.account_id, profile_id, account_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_managers_service.ManagerNotFoundError as exc:
        raise _MANAGER_NOT_FOUND_ERROR from exc
    except profile_managers_service.CannotOrphanProfileError as exc:
        raise _CANNOT_ORPHAN_PROFILE_ERROR from exc
    except profile_managers_service.CannotRevokeCandidateManagerError as exc:
        raise _CANNOT_REVOKE_CANDIDATE_ERROR from exc


@router.post(
    "/{profile_id}/candidate-consent",
    response_model=CandidateConsentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_candidate_consent(
    profile_id: str,
    payload: CandidateConsentRequest,
    current: CurrentSession = Depends(get_current_session),
) -> CandidateConsentResponse:
    try:
        data = profile_managers_service.record_candidate_consent(
            current.account_id, profile_id, payload.decision, payload.granted
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profile_managers_service.CandidateConsentForbiddenError as exc:
        raise _CANDIDATE_CONSENT_FORBIDDEN_ERROR from exc
    return CandidateConsentResponse(**data)


@invitations_router.post(
    "/{token}/accept", response_model=ManagerResponse, status_code=status.HTTP_200_OK
)
async def accept_invitation(
    token: str,
    current: CurrentSession = Depends(get_current_session),
) -> ManagerResponse:
    try:
        data = profile_managers_service.accept_invitation(token, current.account_id)
    except profile_managers_service.InvitationNotFoundError as exc:
        raise _INVITATION_NOT_FOUND_ERROR from exc
    except profile_managers_service.InvitationNotPendingError as exc:
        raise _INVITATION_NOT_PENDING_ERROR from exc
    except profile_managers_service.InvitationEmailMismatchError as exc:
        raise _INVITATION_EMAIL_MISMATCH_ERROR from exc
    return ManagerResponse(**data)

