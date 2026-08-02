"""Profile domain models (catalog §5 — aggregate and lifecycle).

A profile always has at least one manager (the account that created it,
recorded with the ``owner`` role and full permissions). The full manager
invite/accept/revoke system is a later batch; this module only models the
profile aggregate itself.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ProfileRelationship(str, Enum):
    SELF = "self"
    OTHER = "other"


class ProfileStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    PAUSED = "paused"
    DELETING = "deleting"


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Profile(BaseModel):
    id: str
    owner_account_id: str
    relationship: ProfileRelationship
    status: ProfileStatus = ProfileStatus.DRAFT
    version: int = 1
    locale: str = "en"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    submitted_at: datetime | None = None
    published_at: datetime | None = None
    paused_at: datetime | None = None
