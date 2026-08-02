"""Response model for hidden profiles (catalog §7:
`PUT/DELETE /v1/hidden-profiles/{targetProfileId}`).
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HiddenProfileResponse(BaseModel):
    target_profile_id: str
    created_at: datetime
    updated_at: datetime
