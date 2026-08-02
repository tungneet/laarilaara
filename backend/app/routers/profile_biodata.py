"""Router for generated biodata documents (catalog §6:
`POST /v1/profiles/{profileId}/biodata`, `GET /v1/profiles/{profileId}/biodata/{documentId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_biodata import BiodataGenerateRequest, BiodataResponse
from app.services import profile_biodata as profile_biodata_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/profiles", tags=["profiles"])

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

_BIODATA_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_BIODATA_NOT_FOUND",
    title="Biodata document not found",
)


@router.post(
    "/{profile_id}/biodata", response_model=BiodataResponse, status_code=status.HTTP_202_ACCEPTED
)
async def generate_biodata(
    profile_id: str,
    payload: BiodataGenerateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> BiodataResponse:
    try:
        record = profile_biodata_service.generate_biodata(
            current.account_id, profile_id, payload.template, payload.locale
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return BiodataResponse(**record)


@router.get(
    "/{profile_id}/biodata/{document_id}",
    response_model=BiodataResponse,
    status_code=status.HTTP_200_OK,
)
async def get_biodata(
    profile_id: str,
    document_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> BiodataResponse:
    try:
        record = profile_biodata_service.get_biodata(current.account_id, profile_id, document_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_biodata_service.BiodataNotFoundError as exc:
        raise _BIODATA_NOT_FOUND_ERROR from exc
    return BiodataResponse(**record)
