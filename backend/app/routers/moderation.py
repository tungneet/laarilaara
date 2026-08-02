"""Router for moderation-action appeals (catalog §11:
`POST /v1/moderation-actions/{actionId}/appeals`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.moderation import ModerationAppealCreateRequest, ModerationAppealResponse
from app.services import moderation as moderation_service

router = APIRouter(prefix="/v1/moderation-actions", tags=["trust"])

_MODERATION_ACTION_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="MODERATION_ACTION_NOT_FOUND",
    title="Moderation action not found",
)

_MODERATION_APPEAL_WINDOW_EXPIRED_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="MODERATION_APPEAL_WINDOW_EXPIRED",
    title="The appeal window for this action has expired",
)


@router.post(
    "/{action_id}/appeals",
    response_model=ModerationAppealResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_appeal(
    action_id: str,
    payload: ModerationAppealCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> ModerationAppealResponse:
    try:
        appeal = moderation_service.create_appeal(current.account_id, action_id, payload.reason)
    except moderation_service.ModerationActionNotFoundError as exc:
        raise _MODERATION_ACTION_NOT_FOUND_ERROR from exc
    except moderation_service.ModerationAppealWindowExpiredError as exc:
        raise _MODERATION_APPEAL_WINDOW_EXPIRED_ERROR from exc
    return ModerationAppealResponse(**appeal)
