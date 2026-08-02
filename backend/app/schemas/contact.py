"""Contact request/response schemas (/v1/me/contacts)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ContactType(str, Enum):
    EMAIL = "email"
    PHONE = "phone"


class AddContactRequest(BaseModel):
    type: ContactType
    value: str = Field(min_length=3, max_length=254)


class VerifyContactRequest(BaseModel):
    code: str = Field(min_length=4, max_length=16)


class ContactResponse(BaseModel):
    id: str
    type: ContactType
    masked_value: str
    verified: bool
    created_at: datetime
