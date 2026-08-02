"""Router for blocks (catalog §11: `GET/PUT/DELETE /v1/blocks/{targetProfileId}`)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.block import BlockResponse
from app.services import blocks as blocks_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/blocks", tags=["trust"])

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


@router.get("", response_model=list[BlockResponse])
async def list_blocks(
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> list[BlockResponse]:
    try:
        records = blocks_service.list_blocks(current.account_id, acting_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [BlockResponse(**r) for r in records]


@router.put("/{target_profile_id}", response_model=BlockResponse, status_code=status.HTTP_200_OK)
async def block_profile(
    target_profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> BlockResponse:
    try:
        record = blocks_service.block_profile(current.account_id, acting_profile_id, target_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return BlockResponse(**record)


@router.delete("/{target_profile_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def unblock_profile(
    target_profile_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        blocks_service.unblock_profile(current.account_id, acting_profile_id, target_profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
