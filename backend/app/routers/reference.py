"""Public and platform reference endpoints (catalog §3).

All of these are unauthenticated, read-only, and backed by static seed data
(see `app/domain/reference_data.py`) — no DynamoDB round trip. Per the
serverless design doc these are safe candidates for best-effort in-memory
caching in a warm Lambda execution environment, but correctness must never
depend on that; nothing here does.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.config import get_settings
from app.domain import reference_data
from app.schemas.reference import (
    ContextResponse,
    CountryOut,
    LabelOption,
    LanguageOut,
    PlanOut,
    RegionOut,
)

router = APIRouter(tags=["reference"])


@router.get("/v1/context", response_model=ContextResponse, status_code=status.HTTP_200_OK)
async def get_context() -> ContextResponse:
    settings = get_settings()
    return ContextResponse(
        experience="laarilaara",
        service_name=settings.service_name,
        api_version=settings.api_version,
    )


@router.get(
    "/v1/reference/countries",
    response_model=list[CountryOut],
    status_code=status.HTTP_200_OK,
)
async def list_countries() -> list[CountryOut]:
    return [CountryOut(**item) for item in reference_data.COUNTRIES]


@router.get(
    "/v1/reference/regions",
    response_model=list[RegionOut],
    status_code=status.HTTP_200_OK,
)
async def list_regions(
    countryCode: str = Query(..., min_length=2, max_length=2)
) -> list[RegionOut]:
    regions = reference_data.REGIONS_BY_COUNTRY.get(countryCode.upper(), [])
    return [RegionOut(**item) for item in regions]


@router.get(
    "/v1/reference/languages",
    response_model=list[LanguageOut],
    status_code=status.HTTP_200_OK,
)
async def list_languages() -> list[LanguageOut]:
    return [LanguageOut(**item) for item in reference_data.LANGUAGES]


@router.get(
    "/v1/reference/communities",
    response_model=list[LabelOption],
    status_code=status.HTTP_200_OK,
)
async def list_communities() -> list[LabelOption]:
    return [LabelOption(**item) for item in reference_data.COMMUNITIES]


@router.get(
    "/v1/reference/religious-practices",
    response_model=list[LabelOption],
    status_code=status.HTTP_200_OK,
)
async def list_religious_practices() -> list[LabelOption]:
    return [LabelOption(**item) for item in reference_data.RELIGIOUS_PRACTICES]


@router.get(
    "/v1/reference/education-levels",
    response_model=list[LabelOption],
    status_code=status.HTTP_200_OK,
)
async def list_education_levels() -> list[LabelOption]:
    return [LabelOption(**item) for item in reference_data.EDUCATION_LEVELS]


@router.get(
    "/v1/reference/occupation-categories",
    response_model=list[LabelOption],
    status_code=status.HTTP_200_OK,
)
async def list_occupation_categories() -> list[LabelOption]:
    return [LabelOption(**item) for item in reference_data.OCCUPATION_CATEGORIES]


@router.get(
    "/v1/reference/interests",
    response_model=list[LabelOption],
    status_code=status.HTTP_200_OK,
)
async def list_interests() -> list[LabelOption]:
    return [LabelOption(**item) for item in reference_data.INTERESTS]


@router.get("/v1/plans", response_model=list[PlanOut], status_code=status.HTTP_200_OK)
async def list_plans() -> list[PlanOut]:
    return [PlanOut(**item) for item in reference_data.PLANS]
