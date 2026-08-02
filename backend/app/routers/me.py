"""Authenticated account profile endpoint (catalog §4 — GET/PATCH /v1/me)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.repositories import challenges as challenges_repo
from app.repositories import sessions as sessions_repo
from app.schemas.account import MeResponse, UpdateMeRequest
from app.schemas.consent import ConsentRecord, ConsentSummaryResponse, RecordConsentRequest
from app.schemas.contact import AddContactRequest, ContactResponse, VerifyContactRequest
from app.schemas.data_request import CreateDataRequestRequest, DataRequestResponse
from app.schemas.profile import MyProfileItem, MyProfilesResponse
from app.schemas.session import SessionSummary
from app.services import accounts as accounts_service
from app.services import consents as consents_service
from app.services import contacts as contacts_service
from app.services import data_requests as data_requests_service
from app.services import profiles as profiles_service
from app.services import sessions as sessions_service

router = APIRouter(prefix="/v1/me", tags=["account"])

_ACCOUNT_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="ACCOUNT_NOT_FOUND",
    title="Account not found",
)

_SESSION_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="SESSION_NOT_FOUND",
    title="Session not found",
)

_CONTACT_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="CONTACT_NOT_FOUND",
    title="Contact not found",
)

_CONTACT_INVALID_ERROR = ApiError(
    status=status.HTTP_400_BAD_REQUEST,
    code="CONTACT_CHALLENGE_INVALID",
    title="Invalid or expired verification code",
)

_CANNOT_REMOVE_LAST_CONTACT_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="CANNOT_REMOVE_LAST_VERIFIED_CONTACT",
    title="Cannot remove the last verified login contact",
)

_DATA_REQUEST_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="DATA_REQUEST_NOT_FOUND",
    title="Data request not found",
)


def _to_response(account) -> MeResponse:
    return MeResponse(
        id=account.id,
        email=account.email,
        display_name=account.display_name,
        gender=account.gender,
        status=account.status.value,
        tier=account.tier.value,
        locale=account.locale,
        created_at=account.created_at,
    )


def _to_consent_record(item: dict) -> ConsentRecord:
    return ConsentRecord(
        consent_type=item["consentType"],
        granted=item["granted"],
        policy_version=item["policyVersion"],
        decided_at=item["decidedAt"],
    )


def _to_data_request_response(item: dict) -> DataRequestResponse:
    return DataRequestResponse(
        id=item["id"],
        type=item["type"],
        status=item["status"],
        details=item["details"],
        created_at=item["createdAt"],
        completed_at=item["completedAt"],
    )


@router.get("", response_model=MeResponse, status_code=status.HTTP_200_OK)
async def get_me(
    current: CurrentSession = Depends(get_current_session),
) -> MeResponse:
    try:
        account = accounts_service.get_profile(current.account_id)
    except accounts_service.AccountNotFoundError as exc:
        raise _ACCOUNT_NOT_FOUND_ERROR from exc
    return _to_response(account)


@router.get("/profiles", response_model=MyProfilesResponse, status_code=status.HTTP_200_OK)
async def list_my_profiles(
    current: CurrentSession = Depends(get_current_session),
) -> MyProfilesResponse:
    """Every profile the current account manages — the UI's entry point for
    choosing an acting profile after login."""
    items = [
        MyProfileItem(
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
            my_role=manager.get("role", "owner"),
            my_permissions=manager.get("permissions", []),
            is_primary=bool(manager.get("isPrimary", False)),
        )
        for profile, manager in profiles_service.list_my_profiles(current.account_id)
    ]
    return MyProfilesResponse(items=items)


@router.patch("", response_model=MeResponse, status_code=status.HTTP_200_OK)
async def update_me(
    payload: UpdateMeRequest,
    current: CurrentSession = Depends(get_current_session),
) -> MeResponse:
    try:
        account = accounts_service.update_profile(current.account_id, payload.locale)
    except accounts_service.AccountNotFoundError as exc:
        raise _ACCOUNT_NOT_FOUND_ERROR from exc
    return _to_response(account)


@router.get("/sessions", response_model=list[SessionSummary], status_code=status.HTTP_200_OK)
async def list_sessions(
    current: CurrentSession = Depends(get_current_session),
) -> list[SessionSummary]:
    items = sessions_service.list_sessions(current.account_id, current.session_id)
    return [SessionSummary(**item) for item in items]


@router.delete(
    "/sessions/{session_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_session(
    session_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        sessions_service.revoke_session(current.account_id, session_id)
    except sessions_repo.SessionNotFoundError as exc:
        raise _SESSION_NOT_FOUND_ERROR from exc


@router.get(
    "/consents", response_model=ConsentSummaryResponse, status_code=status.HTTP_200_OK
)
async def get_consents(
    current: CurrentSession = Depends(get_current_session),
) -> ConsentSummaryResponse:
    result = consents_service.summary(current.account_id)
    return ConsentSummaryResponse(
        current={
            consent_type: _to_consent_record(item)
            for consent_type, item in result["current"].items()
        },
        history=[_to_consent_record(item) for item in result["history"]],
    )


@router.post(
    "/consents", response_model=ConsentRecord, status_code=status.HTTP_201_CREATED
)
async def record_consent(
    payload: RecordConsentRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ConsentRecord:
    item = consents_service.record(
        current.account_id,
        payload.consent_type.value,
        payload.granted,
        payload.policy_version,
    )
    return _to_consent_record(item)


@router.get(
    "/contacts", response_model=list[ContactResponse], status_code=status.HTTP_200_OK
)
async def list_contacts(
    current: CurrentSession = Depends(get_current_session),
) -> list[ContactResponse]:
    items = contacts_service.list_contacts(current.account_id)
    return [ContactResponse(**item) for item in items]


@router.post(
    "/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
async def add_contact(
    payload: AddContactRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ContactResponse:
    item = contacts_service.add_contact(
        current.account_id, payload.type.value, payload.value
    )
    return ContactResponse(**item)


@router.post(
    "/contacts/{contact_id}/verify",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_contact(
    contact_id: str,
    payload: VerifyContactRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ContactResponse:
    try:
        item = contacts_service.verify_contact(
            current.account_id, contact_id, payload.code
        )
    except contacts_service.ContactNotFoundError as exc:
        raise _CONTACT_NOT_FOUND_ERROR from exc
    except (
        contacts_service.ContactInvalidError,
        challenges_repo.ChallengeNotFoundError,
        challenges_repo.ChallengeInvalidError,
    ) as exc:
        raise _CONTACT_INVALID_ERROR from exc
    return ContactResponse(**item)


@router.delete(
    "/contacts/{contact_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_contact(
    contact_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        contacts_service.remove_contact(current.account_id, contact_id)
    except contacts_service.ContactNotFoundError as exc:
        raise _CONTACT_NOT_FOUND_ERROR from exc
    except contacts_service.CannotRemoveLastVerifiedContactError as exc:
        raise _CANNOT_REMOVE_LAST_CONTACT_ERROR from exc


@router.post(
    "/data-requests",
    response_model=DataRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_data_request(
    payload: CreateDataRequestRequest,
    current: CurrentSession = Depends(get_current_session),
) -> DataRequestResponse:
    item = data_requests_service.create_request(
        current.account_id, payload.type.value, payload.details
    )
    return _to_data_request_response(item)


@router.get(
    "/data-requests/{request_id}",
    response_model=DataRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def get_data_request(
    request_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> DataRequestResponse:
    try:
        item = data_requests_service.get_request(current.account_id, request_id)
    except data_requests_service.DataRequestNotFoundError as exc:
        raise _DATA_REQUEST_NOT_FOUND_ERROR from exc
    return _to_data_request_response(item)
