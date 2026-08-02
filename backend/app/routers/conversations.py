"""Router for conversations and messages (catalog §9: `GET /v1/conversations`,
`GET /v1/conversations/{conversationId}`, `GET/POST /v1/conversations/{id}/messages`,
`PATCH/DELETE /v1/conversations/{id}/messages/{messageId}`,
`POST /v1/conversations/{id}/read`, `POST /v1/conversations/{id}/mute`).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.conversation import (
    ConversationListResponse,
    ConversationMuteRequest,
    ConversationReadRequest,
    ConversationResponse,
    MessageCreateRequest,
    MessageEditRequest,
    MessageListResponse,
    MessageResponse,
)
from app.services import conversations as conversations_service
from app.services import profiles as profiles_service

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)
_CONVERSATION_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="CONVERSATION_NOT_FOUND", title="Conversation not found"
)
_MESSAGE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="MESSAGE_NOT_FOUND", title="Message not found"
)
_MESSAGE_EDIT_WINDOW_EXPIRED_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="MESSAGE_EDIT_WINDOW_EXPIRED",
    title="This message can no longer be edited",
)
_MESSAGE_EMPTY_ERROR = ApiError(
    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    code="MESSAGE_EMPTY",
    title="A message must have a body or an attachment",
)
_MEDIA_ASSET_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="MEDIA_ASSET_NOT_FOUND", title="Media asset not found"
)


def _message_content_blocked_error(exc: conversations_service.MessageContentBlockedError) -> ApiError:
    flagged = [name for name, value in exc.moderation.categories.items() if value]
    return ApiError(
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="MESSAGE_CONTENT_BLOCKED",
        title="Message content was blocked by moderation",
        detail=f"Flagged categories: {', '.join(flagged) or 'unspecified'}",
    )


@router.get("", response_model=ConversationListResponse, status_code=status.HTTP_200_OK)
async def list_conversations(
    acting_profile_id: str = Query(...),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> ConversationListResponse:
    try:
        result = conversations_service.list_conversations(
            current.account_id, acting_profile_id, cursor, limit
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return ConversationListResponse(**result)


@router.get(
    "/{conversation_id}", response_model=ConversationResponse, status_code=status.HTTP_200_OK
)
async def get_conversation(
    conversation_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> ConversationResponse:
    try:
        result = conversations_service.get_conversation(
            current.account_id, acting_profile_id, conversation_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    return ConversationResponse(**result)


@router.get(
    "/{conversation_id}/messages", response_model=MessageListResponse, status_code=status.HTTP_200_OK
)
async def list_messages(
    conversation_id: str,
    acting_profile_id: str = Query(...),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current: CurrentSession = Depends(get_current_session),
) -> MessageListResponse:
    try:
        result = conversations_service.list_messages(
            current.account_id, acting_profile_id, conversation_id, cursor, limit
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    return MessageListResponse(**result)


@router.post(
    "/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
async def send_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MessageResponse:
    try:
        result = await conversations_service.send_message(
            current.account_id,
            acting_profile_id,
            conversation_id,
            payload.client_message_id,
            payload.body,
            payload.attachment_asset_id,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    except conversations_service.MessageEmptyError as exc:
        raise _MESSAGE_EMPTY_ERROR from exc
    except conversations_service.MediaAssetNotFoundError as exc:
        raise _MEDIA_ASSET_NOT_FOUND_ERROR from exc
    except conversations_service.MessageContentBlockedError as exc:
        raise _message_content_blocked_error(exc) from exc
    return MessageResponse(**result)


@router.patch(
    "/{conversation_id}/messages/{message_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def edit_message(
    conversation_id: str,
    message_id: str,
    payload: MessageEditRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MessageResponse:
    try:
        result = await conversations_service.edit_message(
            current.account_id, acting_profile_id, conversation_id, message_id, payload.body
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    except conversations_service.MessageNotFoundError as exc:
        raise _MESSAGE_NOT_FOUND_ERROR from exc
    except conversations_service.MessageEditWindowExpiredError as exc:
        raise _MESSAGE_EDIT_WINDOW_EXPIRED_ERROR from exc
    return MessageResponse(**result)


@router.delete(
    "/{conversation_id}/messages/{message_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_message(
    conversation_id: str,
    message_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> MessageResponse:
    try:
        result = await conversations_service.delete_message(
            current.account_id, acting_profile_id, conversation_id, message_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    except conversations_service.MessageNotFoundError as exc:
        raise _MESSAGE_NOT_FOUND_ERROR from exc
    return MessageResponse(**result)


@router.post(
    "/{conversation_id}/read", response_model=ConversationResponse, status_code=status.HTTP_200_OK
)
async def mark_read(
    conversation_id: str,
    payload: ConversationReadRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> ConversationResponse:
    try:
        result = await conversations_service.mark_read(
            current.account_id, acting_profile_id, conversation_id, payload.message_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    except conversations_service.MessageNotFoundError as exc:
        raise _MESSAGE_NOT_FOUND_ERROR from exc
    return ConversationResponse(**result)


@router.post(
    "/{conversation_id}/mute", response_model=ConversationResponse, status_code=status.HTTP_200_OK
)
async def set_mute(
    conversation_id: str,
    payload: ConversationMuteRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> ConversationResponse:
    try:
        result = conversations_service.set_mute(
            current.account_id, acting_profile_id, conversation_id, payload.muted
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    return ConversationResponse(**result)
