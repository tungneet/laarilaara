"""Router for compatibility analyses (catalog §8:
`POST /v1/compatibility-analyses`, `GET /v1/compatibility-analyses/{analysisId}`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.compatibility import (
    CompatibilityAnalysisCreateRequest,
    CompatibilityAnalysisResponse,
)
from app.services import compatibility as compatibility_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/compatibility-analyses", tags=["compatibility"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)
_ANALYSIS_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="COMPATIBILITY_ANALYSIS_NOT_FOUND",
    title="Compatibility analysis not found",
)


@router.post("", response_model=CompatibilityAnalysisResponse, status_code=status.HTTP_200_OK)
async def create_analysis(
    payload: CompatibilityAnalysisCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> CompatibilityAnalysisResponse:
    try:
        result = compatibility_service.create_or_refresh_analysis(
            current.account_id, acting_profile_id, payload.target_profile_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return CompatibilityAnalysisResponse(**result)


@router.get(
    "/{analysis_id}", response_model=CompatibilityAnalysisResponse, status_code=status.HTTP_200_OK
)
async def get_analysis(
    analysis_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> CompatibilityAnalysisResponse:
    try:
        result = compatibility_service.get_analysis(current.account_id, acting_profile_id, analysis_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except compatibility_service.AnalysisNotFoundError as exc:
        raise _ANALYSIS_NOT_FOUND_ERROR from exc
    return CompatibilityAnalysisResponse(**result)
