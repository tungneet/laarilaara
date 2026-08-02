"""Routers for §11 trust-summary and verification endpoints.

Split into two `APIRouter`s (same reason as `app/routers/ai.py`'s 5-router
split): the catalog paths span two different prefixes —
`/v1/profiles/{profileId}/...` and `/v1/verification-requests/{requestId}`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.verification import (
    TrustSummaryResponse,
    VerificationCheckOption,
    VerificationClaim,
    VerificationEvidenceCreateRequest,
    VerificationRequestCreateRequest,
    VerificationRequestResponse,
)
from app.services import profiles as profiles_service
from app.services import verification as verification_service

profile_verification_router = APIRouter(prefix="/v1/profiles", tags=["trust"])
verification_requests_router = APIRouter(prefix="/v1/verification-requests", tags=["trust"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_NOT_FOUND",
    title="Profile not found",
)

_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)

_VERIFICATION_REQUEST_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="VERIFICATION_REQUEST_NOT_FOUND",
    title="Verification request not found",
)

_VERIFICATION_EVIDENCE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="MEDIA_ASSET_NOT_FOUND",
    title="Evidence media asset not found",
)

_VERIFICATION_REQUEST_ALREADY_SUBMITTED_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="VERIFICATION_REQUEST_ALREADY_SUBMITTED",
    title="Verification request already submitted",
)

_VERIFICATION_EVIDENCE_REQUIRED_ERROR = ApiError(
    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    code="VERIFICATION_EVIDENCE_REQUIRED",
    title="At least one evidence asset is required before submitting",
)


@profile_verification_router.get("/{profile_id}/trust-summary", response_model=TrustSummaryResponse)
async def get_trust_summary(
    profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> TrustSummaryResponse:
    try:
        summary = verification_service.trust_summary(current.account_id, acting_profile_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return TrustSummaryResponse(**summary)


@profile_verification_router.get(
    "/{profile_id}/verification-options", response_model=list[VerificationCheckOption]
)
async def get_verification_options(
    profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> list[VerificationCheckOption]:
    try:
        profiles_service.require_permission(acting_profile_id, current.account_id, "profile.read_private")
        profiles_service.get_or_404(profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [VerificationCheckOption(**opt) for opt in verification_service.list_options()]


@profile_verification_router.post(
    "/{profile_id}/verification-requests",
    response_model=VerificationRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_verification_request(
    profile_id: str,
    payload: VerificationRequestCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> VerificationRequestResponse:
    try:
        request = verification_service.create_request(current.account_id, profile_id, payload.check_type)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return VerificationRequestResponse(**request)


@profile_verification_router.get(
    "/{profile_id}/verification-claims", response_model=list[VerificationClaim]
)
async def get_verification_claims(
    profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> list[VerificationClaim]:
    try:
        claims = verification_service.get_claims(current.account_id, acting_profile_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [VerificationClaim(**c) for c in claims]


@verification_requests_router.get("/{request_id}", response_model=VerificationRequestResponse)
async def get_verification_request(
    request_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> VerificationRequestResponse:
    try:
        request = verification_service.get_request(current.account_id, acting_profile_id, request_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except verification_service.VerificationRequestNotFoundError as exc:
        raise _VERIFICATION_REQUEST_NOT_FOUND_ERROR from exc
    return VerificationRequestResponse(**request)


@verification_requests_router.post(
    "/{request_id}/evidence", response_model=VerificationRequestResponse
)
async def add_verification_evidence(
    request_id: str,
    payload: VerificationEvidenceCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> VerificationRequestResponse:
    try:
        request = verification_service.add_evidence(
            current.account_id, acting_profile_id, request_id, payload.asset_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except verification_service.VerificationRequestNotFoundError as exc:
        raise _VERIFICATION_REQUEST_NOT_FOUND_ERROR from exc
    except verification_service.VerificationRequestAlreadySubmittedError as exc:
        raise _VERIFICATION_REQUEST_ALREADY_SUBMITTED_ERROR from exc
    except verification_service.VerificationEvidenceAssetNotFoundError as exc:
        raise _VERIFICATION_EVIDENCE_NOT_FOUND_ERROR from exc
    return VerificationRequestResponse(**request)


@verification_requests_router.post(
    "/{request_id}/submit",
    response_model=VerificationRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_verification_request(
    request_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> VerificationRequestResponse:
    try:
        request = verification_service.submit_request(current.account_id, acting_profile_id, request_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except verification_service.VerificationRequestNotFoundError as exc:
        raise _VERIFICATION_REQUEST_NOT_FOUND_ERROR from exc
    except verification_service.VerificationEvidenceRequiredError as exc:
        raise _VERIFICATION_EVIDENCE_REQUIRED_ERROR from exc
    return VerificationRequestResponse(**request)
