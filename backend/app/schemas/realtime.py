"""Request/response models for the realtime WebSocket half (catalog §9:
`POST /v1/realtime-tokens`).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RealtimeTokenRequest(BaseModel):
    profile_id: str = Field(min_length=1)


class RealtimeTokenResponse(BaseModel):
    token: str
    expires_in: int
