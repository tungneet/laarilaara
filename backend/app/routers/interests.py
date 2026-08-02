"""Router for interests (catalog §8: `GET/POST /v1/interests`,
`POST /v1/interests/{interestId}/accept|decline|withdraw`).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.interest import (
    InterestCreateRequest,
    InterestDeclineRequest,
    InterestListResponse,
    InterestResponse,
)
from app.services import interests as interests_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/interests", tags=["interests"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)
_INTEREST_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="INTEREST_NOT_FOUND", title="Interest not found"
)


def _conflict_error(exc: interests_service.InterestStateConflictError) -> ApiError:
    return ApiError(
        status=status.HTTP_409_CONFLICT,
        code="INTEREST_STATE_CONFLICT",
        title="Interest is not in the required state",
        detail=f"expected status '{exc.expected}', got '{exc.actual}'",
    )


_SELF_TARGET_ERROR = ApiError(
    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    code="INTEREST_SELF_TARGET",
    title="Cannot send an interest to your own profile",
)


@router.get("", response_model=InterestListResponse, status_code=status.HTTP_200_OK)
async def list_interests(
    acting_profile_id: str = Query(...),
    direction: Literal["incoming", "outgoing"] = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> InterestListResponse:
    try:
        result = interests_service.list_interests(
            current.account_id, acting_profile_id, direction, status_filter, cursor, limit
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return InterestListResponse(**result)


@router.post("", response_model=InterestResponse, status_code=status.HTTP_201_CREATED)
async def send_interest(
    payload: InterestCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> InterestResponse:
    try:
        result = interests_service.send_interest(
            current.account_id, acting_profile_id, payload.target_profile_id, payload.message
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except interests_service.InterestSelfTargetError as exc:
        raise _SELF_TARGET_ERROR from exc
    return InterestResponse(**result)


@router.post("/{interest_id}/accept", response_model=InterestResponse, status_code=status.HTTP_200_OK)
async def accept_interest(
    interest_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> InterestResponse:
    try:
        result = interests_service.accept_interest(current.account_id, acting_profile_id, interest_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except interests_service.InterestNotFoundError as exc:
        raise _INTEREST_NOT_FOUND_ERROR from exc
    except interests_service.InterestStateConflictError as exc:
        raise _conflict_error(exc) from exc
    return InterestResponse(**result)


@router.post("/{interest_id}/decline", response_model=InterestResponse, status_code=status.HTTP_200_OK)
async def decline_interest(
    interest_id: str,
    payload: InterestDeclineRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> InterestResponse:
    try:
        result = interests_service.decline_interest(
            current.account_id, acting_profile_id, interest_id, payload.reason
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except interests_service.InterestNotFoundError as exc:
        raise _INTEREST_NOT_FOUND_ERROR from exc
    except interests_service.InterestStateConflictError as exc:
        raise _conflict_error(exc) from exc
    return InterestResponse(**result)


@router.post("/{interest_id}/withdraw", response_model=InterestResponse, status_code=status.HTTP_200_OK)
async def withdraw_interest(
    interest_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> InterestResponse:
    try:
        result = interests_service.withdraw_interest(current.account_id, acting_profile_id, interest_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except interests_service.InterestNotFoundError as exc:
        raise _INTEREST_NOT_FOUND_ERROR from exc
    except interests_service.InterestStateConflictError as exc:
        raise _conflict_error(exc) from exc
    return InterestResponse(**result)
