"""Request/response models for messaging (catalog §9: `GET /v1/conversations`,
`GET /v1/conversations/{conversationId}`, `GET/POST /v1/conversations/{id}/messages`,
`PATCH/DELETE /v1/conversations/{id}/messages/{messageId}`,
`POST /v1/conversations/{id}/read`, `POST /v1/conversations/{id}/mute`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MessageStatus = Literal["sent", "edited", "deleted"]


class ConversationResponse(BaseModel):
    id: str
    match_id: str
    profile_a_id: str
    profile_b_id: str
    last_message_at: datetime | None = None
    last_message_preview: str | None = None
    unread_count: int
    muted: bool
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    next_cursor: str | None = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_profile_id: str
    client_message_id: str
    body: str | None = None
    attachment_asset_id: str | None = None
    status: MessageStatus
    revision: int
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None = None
    deleted_at: datetime | None = None


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    next_cursor: str | None = None


class MessageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_message_id: str = Field(min_length=1, max_length=128)
    body: str | None = Field(default=None, max_length=5000)
    attachment_asset_id: str | None = None


class MessageEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=5000)


class ConversationReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: str


class ConversationMuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muted: bool
