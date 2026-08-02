"""Router for education and employment records (catalog §5 — "Sections"
batch C: `GET/POST .../education`, `GET/PATCH/DELETE .../education/{id}`,
and the equivalent employment endpoints).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.profile_records import (
    EducationCreateRequest,
    EducationPatchRequest,
    EducationResponse,
    EmploymentCreateRequest,
    EmploymentPatchRequest,
    EmploymentResponse,
)
from app.services import profile_records as profile_records_service
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

_EDUCATION_RECORD_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_EDUCATION_RECORD_NOT_FOUND",
    title="Education record not found",
)

_EMPLOYMENT_RECORD_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="PROFILE_EMPLOYMENT_RECORD_NOT_FOUND",
    title="Employment record not found",
)


def _invalid_value_error(exc: profile_records_service.InvalidRecordValueError) -> ApiError:
    return ApiError(
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="PROFILE_RECORD_INVALID_VALUE",
        title="Field is not a recognized option",
        detail=f"Invalid {exc.field}: {exc.value}",
    )


@router.get(
    "/{profile_id}/education",
    response_model=list[EducationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_education(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> list[EducationResponse]:
    try:
        records = profile_records_service.list_education(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [EducationResponse(**r) for r in records]


@router.post(
    "/{profile_id}/education",
    response_model=EducationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_education(
    profile_id: str,
    payload: EducationCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> EducationResponse:
    try:
        record = profile_records_service.add_education(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.InvalidRecordValueError as exc:
        raise _invalid_value_error(exc) from exc
    return EducationResponse(**record)


@router.get(
    "/{profile_id}/education/{record_id}",
    response_model=EducationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_education_record(
    profile_id: str,
    record_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> EducationResponse:
    try:
        record = profile_records_service.get_education_record(
            current.account_id, profile_id, record_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.RecordNotFoundError as exc:
        raise _EDUCATION_RECORD_NOT_FOUND_ERROR from exc
    return EducationResponse(**record)


@router.patch(
    "/{profile_id}/education/{record_id}",
    response_model=EducationResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_education_record(
    profile_id: str,
    record_id: str,
    payload: EducationPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> EducationResponse:
    try:
        record = profile_records_service.patch_education_record(
            current.account_id, profile_id, record_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.RecordNotFoundError as exc:
        raise _EDUCATION_RECORD_NOT_FOUND_ERROR from exc
    except profile_records_service.InvalidRecordValueError as exc:
        raise _invalid_value_error(exc) from exc
    return EducationResponse(**record)


@router.delete(
    "/{profile_id}/education/{record_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_education_record(
    profile_id: str,
    record_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        profile_records_service.delete_education_record(
            current.account_id, profile_id, record_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.RecordNotFoundError as exc:
        raise _EDUCATION_RECORD_NOT_FOUND_ERROR from exc


@router.get(
    "/{profile_id}/employment",
    response_model=list[EmploymentResponse],
    status_code=status.HTTP_200_OK,
)
async def list_employment(
    profile_id: str, current: CurrentSession = Depends(get_current_session)
) -> list[EmploymentResponse]:
    try:
        records = profile_records_service.list_employment(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return [EmploymentResponse(**r) for r in records]


@router.post(
    "/{profile_id}/employment",
    response_model=EmploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_employment(
    profile_id: str,
    payload: EmploymentCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> EmploymentResponse:
    try:
        record = profile_records_service.add_employment(
            current.account_id, profile_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.InvalidRecordValueError as exc:
        raise _invalid_value_error(exc) from exc
    return EmploymentResponse(**record)


@router.get(
    "/{profile_id}/employment/{record_id}",
    response_model=EmploymentResponse,
    status_code=status.HTTP_200_OK,
)
async def get_employment_record(
    profile_id: str,
    record_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> EmploymentResponse:
    try:
        record = profile_records_service.get_employment_record(
            current.account_id, profile_id, record_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.RecordNotFoundError as exc:
        raise _EMPLOYMENT_RECORD_NOT_FOUND_ERROR from exc
    return EmploymentResponse(**record)


@router.patch(
    "/{profile_id}/employment/{record_id}",
    response_model=EmploymentResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_employment_record(
    profile_id: str,
    record_id: str,
    payload: EmploymentPatchRequest,
    current: CurrentSession = Depends(get_current_session),
) -> EmploymentResponse:
    try:
        record = profile_records_service.patch_employment_record(
            current.account_id, profile_id, record_id, payload.model_dump(mode="json")
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.RecordNotFoundError as exc:
        raise _EMPLOYMENT_RECORD_NOT_FOUND_ERROR from exc
    except profile_records_service.InvalidRecordValueError as exc:
        raise _invalid_value_error(exc) from exc
    return EmploymentResponse(**record)


@router.delete(
    "/{profile_id}/employment/{record_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_employment_record(
    profile_id: str,
    record_id: str,
    current: CurrentSession = Depends(get_current_session),
) -> None:
    try:
        profile_records_service.delete_employment_record(
            current.account_id, profile_id, record_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except profile_records_service.RecordNotFoundError as exc:
        raise _EMPLOYMENT_RECORD_NOT_FOUND_ERROR from exc
