"""Request/response models for §10 AI-assisted domain endpoints.

All generation endpoints share the same response shape: an ``AiArtifactResponse``
that doubles as the catalog's ``Operation`` resource (see
`app/repositories/ai_artifacts.py`). See `app/services/ai.py` for the full
list of documented known gaps (no async worker exists, so every artifact
stays ``queued`` forever).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactStatus = Literal["queued", "running", "succeeded", "failed", "canceled", "expired"]


class AiArtifactSubject(BaseModel):
    type: str
    id: str
    version: int | None = None


class AiArtifactResponse(BaseModel):
    id: str
    kind: str
    status: ArtifactStatus
    subject: AiArtifactSubject
    result: dict | None = None
    error: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ExtractionDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=5000)


class BioDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tone: str | None = Field(default=None, max_length=32)


class QualityAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AiArtifactApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_profile_version: int


class SearchDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)


class CompatibilityExplanationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AssistantDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=1, max_length=32)
    tone: str | None = Field(default=None, max_length=32)
    locale: str | None = Field(default=None, max_length=16)


class TranslationDraftCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_locale: str = Field(min_length=1, max_length=16)
    message_id: str | None = None
    text: str | None = Field(default=None, max_length=5000)


class ToneCheckCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=5000)


class AiArtifactFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int = Field(ge=1, le=5)
    category: str | None = Field(default=None, max_length=64)


class AiArtifactFeedbackResponse(BaseModel):
    artifact_id: str
    profile_id: str
    rating: int
    category: str | None
    created_at: datetime
