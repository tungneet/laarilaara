"""Response model for §14 provider webhook acknowledgements."""
from __future__ import annotations

from pydantic import BaseModel


class WebhookAckResponse(BaseModel):
    received: bool = True
    duplicate: bool = False
