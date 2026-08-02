"""Request/response models for §11 blocks (`GET/PUT/DELETE /v1/blocks/...`)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BlockResponse(BaseModel):
    target_profile_id: str
    created_at: datetime
    updated_at: datetime
