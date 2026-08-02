"""Router for matches (catalog §8: `GET /v1/matches`, `GET /v1/matches/{matchId}`,
`POST /v1/matches/{matchId}/end|feedback|outcomes`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.match import (
    MatchFeedbackRequest,
    MatchFeedbackResponse,
    MatchListResponse,
    MatchOutcomeRequest,
    MatchOutcomeResponse,
    MatchResponse,
)
from app.services import matches as matches_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/matches", tags=["matches"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)
_MATCH_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="MATCH_NOT_FOUND", title="Match not found"
)
_OUTCOME_CONSENT_REQUIRED_ERROR = ApiError(
    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    code="MATCH_OUTCOME_CONSENT_REQUIRED",
    title="Explicit consent is required to record a match outcome",
)


@router.get("", response_model=MatchListResponse, status_code=status.HTTP_200_OK)
async def list_matches(
    acting_profile_id: str = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> MatchListResponse:
    try:
        result = matches_service.list_matches(
            current.account_id, acting_profile_id, status_filter, cursor, limit
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return MatchListResponse(**result)


@router.get("/{match_id}", response_model=MatchResponse, status_code=status.HTTP_200_OK)
async def get_match(
    match_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MatchResponse:
    try:
        result = matches_service.get_match(current.account_id, acting_profile_id, match_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except matches_service.MatchNotFoundError as exc:
        raise _MATCH_NOT_FOUND_ERROR from exc
    return MatchResponse(**result)


@router.post("/{match_id}/end", response_model=MatchResponse, status_code=status.HTTP_200_OK)
async def end_match(
    match_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MatchResponse:
    try:
        result = matches_service.end_match(current.account_id, acting_profile_id, match_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except matches_service.MatchNotFoundError as exc:
        raise _MATCH_NOT_FOUND_ERROR from exc
    return MatchResponse(**result)


@router.post(
    "/{match_id}/feedback", response_model=MatchFeedbackResponse, status_code=status.HTTP_201_CREATED
)
async def submit_feedback(
    match_id: str,
    payload: MatchFeedbackRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MatchFeedbackResponse:
    try:
        result = matches_service.submit_feedback(
            current.account_id, acting_profile_id, match_id, payload.rating, payload.comment
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except matches_service.MatchNotFoundError as exc:
        raise _MATCH_NOT_FOUND_ERROR from exc
    return MatchFeedbackResponse(**result)


@router.post(
    "/{match_id}/outcomes", response_model=MatchOutcomeResponse, status_code=status.HTTP_201_CREATED
)
async def submit_outcome(
    match_id: str,
    payload: MatchOutcomeRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MatchOutcomeResponse:
    try:
        result = matches_service.submit_outcome(
            current.account_id, acting_profile_id, match_id, payload.outcome, payload.consent
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except matches_service.MatchNotFoundError as exc:
        raise _MATCH_NOT_FOUND_ERROR from exc
    except matches_service.OutcomeConsentRequiredError as exc:
        raise _OUTCOME_CONSENT_REQUIRED_ERROR from exc
    return MatchOutcomeResponse(**result)
