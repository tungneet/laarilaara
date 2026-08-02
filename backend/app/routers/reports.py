"""Router for reports (catalog §11: `POST/GET /v1/reports`)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.services import profiles as profiles_service
from app.services import reports as reports_service

router = APIRouter(prefix="/v1/reports", tags=["trust"])

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

_REPORT_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="REPORT_NOT_FOUND",
    title="Report not found",
)

_REPORT_EVIDENCE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="MEDIA_ASSET_NOT_FOUND",
    title="Evidence media asset not found",
)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    payload: ReportCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> ReportResponse:
    try:
        report = reports_service.create_report(
            current.account_id,
            acting_profile_id,
            payload.subject_type,
            payload.subject_id,
            payload.reason,
            payload.details,
            payload.evidence_asset_ids,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except reports_service.ReportEvidenceNotFoundError as exc:
        raise _REPORT_EVIDENCE_NOT_FOUND_ERROR from exc
    return ReportResponse(**report)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> ReportResponse:
    try:
        report = reports_service.get_report(current.account_id, acting_profile_id, report_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except reports_service.ReportNotFoundError as exc:
        raise _REPORT_NOT_FOUND_ERROR from exc
    return ReportResponse(**report)
