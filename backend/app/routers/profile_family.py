"""Router for the family section (catalog §5 — "Sections" batch D):
`GET/PUT .../family`, `GET/POST .../family/members`,
`PATCH/DELETE .../family/members/{memberId}`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_family import (
    FamilyMemberCreateRequest,
    FamilyMemberPatchRequest,
    FamilyMemberResponse,
    FamilyPutRequest,
    FamilyResponse,
)
from app.services import profile_family as profile_family_service
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

_FAMILY_MEMBER_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_FAMILY_MEMBER_NOT_FOUND",
    title="Family member not found",
)


@router.get(
    "/{profile_id}/family",
    response_model=FamilyResponse,
    status_code=status.HTTP_200_OK,
)
async def get_family(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> FamilyResponse:
    try:
        section = profile_family_service.get_family(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return FamilyResponse(**section)


@router.put(
    "/{profile_id}/family",
    response_model=FamilyResponse,
    status_code=status.HTTP_200_OK,
)
async def put_family(
    profile_id: str,
    payload: FamilyPutRequest,
    current: CurrentSession = Depends(get_current_session),
) -> FamilyResponse:
    try:
        section = profile_family_service.put_family(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return FamilyResponse(**section)


@router.get(
    "/{profile_id}/family/members",
    response_model=list[FamilyMemberResponse],
    status_code=status.HTTP_200_OK,
)
async def list_family_members(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> list[FamilyMemberResponse]:
    try:
        records = profile_family_service.list_family_members(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [FamilyMemberResponse(**r) for r in records]


@router.post(
    "/{profile_id}/family/members",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_family_member(
    profile_id: str,
    payload: FamilyMemberCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> FamilyMemberResponse:
    try:
        record = profile_family_service.add_family_member(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return FamilyMemberResponse(**record)


@router.patch(
    "/{profile_id}/family/members/{member_id}",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_family_member(
    profile_id: str,
    member_id: str,
    payload: FamilyMemberPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> FamilyMemberResponse:
    try:
        record = profile_family_service.patch_family_member(
            current.account_id, profile_id, member_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_family_service.RecordNotFoundError as exc:
        raise _FAMILY_MEMBER_NOT_FOUND_ERROR from exc
    return FamilyMemberResponse(**record)


@router.delete(
    "/{profile_id}/family/members/{member_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_family_member(
    profile_id: str,
    member_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        profile_family_service.delete_family_member(current.account_id, profile_id, member_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_family_service.RecordNotFoundError as exc:
        raise _FAMILY_MEMBER_NOT_FOUND_ERROR from exc
