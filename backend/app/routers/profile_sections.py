"""Router for single-resource profile sections (catalog §5 — "Sections"
batch: personal-details, narratives, lifestyle, visibility).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_sections import (
    LifestylePatchRequest,
    LifestyleResponse,
    NarrativesPatchRequest,
    NarrativesResponse,
    PersonalDetailsPatchRequest,
    PersonalDetailsResponse,
    VisibilityPatchRequest,
    VisibilityResponse,
)
from app.services import profile_sections as profile_sections_service
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


def _narrative_content_blocked_error(
    exc: profile_sections_service.NarrativeContentBlockedError,
) -> ApiError:
    flagged = [name for name, value in exc.moderation.categories.items() if value]
    return ApiError(
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="NARRATIVE_CONTENT_BLOCKED",
        title="Narrative content was blocked by moderation",
        detail=f"Field '{exc.field_name}' flagged categories: {', '.join(flagged) or 'unspecified'}",
    )


@router.get(
    "/{profile_id}/personal-details",
    response_model=PersonalDetailsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_personal_details(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> PersonalDetailsResponse:
    try:
        data = profile_sections_service.get_personal_details(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return PersonalDetailsResponse(**data)


@router.patch(
    "/{profile_id}/personal-details",
    response_model=PersonalDetailsResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_personal_details(
    profile_id: str,
    payload: PersonalDetailsPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> PersonalDetailsResponse:
    try:
        data = profile_sections_service.patch_personal_details(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return PersonalDetailsResponse(**data)


@router.get(
    "/{profile_id}/narratives",
    response_model=NarrativesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_narratives(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> NarrativesResponse:
    try:
        data = profile_sections_service.get_narratives(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return NarrativesResponse(**data)


@router.patch(
    "/{profile_id}/narratives",
    response_model=NarrativesResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_narratives(
    profile_id: str,
    payload: NarrativesPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> NarrativesResponse:
    try:
        data = profile_sections_service.patch_narratives(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_sections_service.NarrativeContentBlockedError as exc:
        raise _narrative_content_blocked_error(exc) from exc
    return NarrativesResponse(**data)


@router.get(
    "/{profile_id}/lifestyle",
    response_model=LifestyleResponse,
    status_code=status.HTTP_200_OK,
)
async def get_lifestyle(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> LifestyleResponse:
    try:
        data = profile_sections_service.get_lifestyle(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return LifestyleResponse(**data)


@router.patch(
    "/{profile_id}/lifestyle",
    response_model=LifestyleResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_lifestyle(
    profile_id: str,
    payload: LifestylePatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> LifestyleResponse:
    try:
        data = profile_sections_service.patch_lifestyle(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return LifestyleResponse(**data)


@router.get(
    "/{profile_id}/visibility",
    response_model=VisibilityResponse,
    status_code=status.HTTP_200_OK,
)
async def get_visibility(
    profile_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> VisibilityResponse:
    try:
        data = profile_sections_service.get_visibility(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return VisibilityResponse(**data)


@router.patch(
    "/{profile_id}/visibility",
    response_model=VisibilityResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_visibility(
    profile_id: str,
    payload: VisibilityPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> VisibilityResponse:
    try:
        data = profile_sections_service.patch_visibility(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return VisibilityResponse(**data)
