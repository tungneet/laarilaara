"""Session summary schemas for the /v1/me/sessions surface."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionSummary(BaseModel):
    id: str
    created_at: datetime
    expires_at: datetime
    is_current: bool
