"""Request/response models for §12 notifications, notification-preferences,
and push-endpoints.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    id: str
    category: str
    title: str
    body: str
    data: dict
    created_at: datetime
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    next_cursor: str | None = None


class MarkAllReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    through: datetime | None = None


class NotificationPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: dict[str, list[str]]


class NotificationPreferencesResponse(BaseModel):
    categories: dict[str, list[str]]
    updated_at: datetime | None = None


class PushEndpointCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1, max_length=32)
    token: str = Field(min_length=1, max_length=4096)


class PushEndpointResponse(BaseModel):
    id: str
    platform: str
    created_at: datetime
