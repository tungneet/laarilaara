"""Router for profile media attachments (catalog §6:
`GET/POST /v1/profiles/{profileId}/media`,
`PATCH/DELETE /v1/profiles/{profileId}/media/{profileMediaId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_media import (
    ProfileMediaCreateRequest,
    ProfileMediaPatchRequest,
    ProfileMediaResponse,
)
from app.services import profile_media as profile_media_service
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

_MEDIA_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_MEDIA_NOT_FOUND",
    title="Profile media not found",
)

_ASSET_NOT_READY_ERROR = ApiError(
    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    code="PROFILE_MEDIA_ASSET_NOT_READY",
    title="Media asset is not ready to be attached",
)

_ASSET_NOT_OWNED_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_MEDIA_ASSET_NOT_OWNED",
    title="Media asset does not belong to the current account",
)


@router.get(
    "/{profile_id}/media", response_model=list[ProfileMediaResponse], status_code=status.HTTP_200_OK
)
async def list_media(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> list[ProfileMediaResponse]:
    try:
        records = profile_media_service.list_media(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [ProfileMediaResponse(**r) for r in records]


@router.post(
    "/{profile_id}/media", response_model=ProfileMediaResponse, status_code=status.HTTP_201_CREATED
)
async def attach_media(
    profile_id: str,
    payload: ProfileMediaCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileMediaResponse:
    try:
        record = profile_media_service.attach_media(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_media_service.RecordNotFoundError as exc:
        raise ApiError(
            status=status.HTTP_404_NOT_FOUND,
            code="MEDIA_ASSET_NOT_FOUND",
            title="Media asset not found",
        ) from exc
    except profile_media_service.AssetNotOwnedError as exc:
        raise _ASSET_NOT_OWNED_ERROR from exc
    except profile_media_service.AssetNotReadyError as exc:
        raise _ASSET_NOT_READY_ERROR from exc
    return ProfileMediaResponse(**record)


@router.patch(
    "/{profile_id}/media/{media_id}",
    response_model=ProfileMediaResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_media(
    profile_id: str,
    media_id: str,
    payload: ProfileMediaPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ProfileMediaResponse:
    try:
        record = profile_media_service.patch_media(
            current.account_id, profile_id, media_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_media_service.RecordNotFoundError as exc:
        raise _MEDIA_NOT_FOUND_ERROR from exc
    return ProfileMediaResponse(**record)


@router.delete(
    "/{profile_id}/media/{media_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT
)
async def delete_media(
    profile_id: str,
    media_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        profile_media_service.delete_media(current.account_id, profile_id, media_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_media_service.RecordNotFoundError as exc:
        raise _MEDIA_NOT_FOUND_ERROR from exc
