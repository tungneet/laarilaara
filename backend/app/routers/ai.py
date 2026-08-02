"""Routers for catalog §10 "AI-assisted domain endpoints".

Split into five small `APIRouter`s (rather than one) because the 11 catalog
paths are scattered across five different resource prefixes
(`/v1/profiles/...`, `/v1/discovery/...`, `/v1/compatibility-analyses/...`,
`/v1/conversations/...`, `/v1/ai-artifacts/...`) — all five are registered in
`main.py`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.schemas.ai import (
    AiArtifactApplyRequest,
    AiArtifactFeedbackRequest,
    AiArtifactFeedbackResponse,
    AiArtifactResponse,
    AssistantDraftCreateRequest,
    BioDraftCreateRequest,
    CompatibilityExplanationCreateRequest,
    ExtractionDraftCreateRequest,
    QualityAnalysisCreateRequest,
    SearchDraftCreateRequest,
    ToneCheckCreateRequest,
    TranslationDraftCreateRequest,
)
from app.services import ai as ai_service
from app.services import compatibility as compatibility_service
from app.services import conversations as conversations_service
from app.services import profiles as profiles_service

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)
_ARTIFACT_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="AI_ARTIFACT_NOT_FOUND", title="AI artifact not found"
)
_ARTIFACT_NOT_READY_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="AI_ARTIFACT_NOT_READY",
    title="This artifact has not finished generating yet",
)
_ARTIFACT_VERSION_MISMATCH_ERROR = ApiError(
    status=status.HTTP_409_CONFLICT,
    code="AI_ARTIFACT_VERSION_MISMATCH",
    title="The profile has changed since this artifact was generated",
)
_ANALYSIS_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="COMPATIBILITY_ANALYSIS_NOT_FOUND",
    title="Compatibility analysis not found",
)
_CONVERSATION_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="CONVERSATION_NOT_FOUND", title="Conversation not found"
)
_TRANSLATION_DRAFT_INPUT_ERROR = ApiError(
    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
    code="TRANSLATION_DRAFT_INPUT_REQUIRED",
    title="Either message_id or text must be supplied",
)

profile_ai_router = APIRouter(prefix="/v1/profiles", tags=["ai"])
discovery_ai_router = APIRouter(prefix="/v1/discovery", tags=["ai"])
compatibility_ai_router = APIRouter(prefix="/v1/compatibility-analyses", tags=["ai"])
conversation_ai_router = APIRouter(prefix="/v1/conversations", tags=["ai"])
artifacts_router = APIRouter(prefix="/v1/ai-artifacts", tags=["ai"])


@profile_ai_router.post(
    "/{profile_id}/ai/extraction-drafts",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_extraction_draft(
    profile_id: str,
    payload: ExtractionDraftCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_extraction_draft(current.account_id, profile_id, payload.text)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return AiArtifactResponse(**result)


@profile_ai_router.post(
    "/{profile_id}/ai/bio-drafts",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_bio_draft(
    profile_id: str,
    payload: BioDraftCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_bio_draft(current.account_id, profile_id, payload.tone)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return AiArtifactResponse(**result)


@profile_ai_router.post(
    "/{profile_id}/ai/quality-analyses",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_quality_analysis(
    profile_id: str,
    payload: QualityAnalysisCreateRequest,
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_quality_analysis(current.account_id, profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return AiArtifactResponse(**result)


@profile_ai_router.post(
    "/{profile_id}/ai-artifacts/{artifact_id}/apply",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_200_OK,
)
async def apply_artifact(
    profile_id: str,
    artifact_id: str,
    payload: AiArtifactApplyRequest,
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.apply_artifact(
            current.account_id, profile_id, artifact_id, payload.expected_profile_version
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except ai_service.ArtifactNotFoundError as exc:
        raise _ARTIFACT_NOT_FOUND_ERROR from exc
    except ai_service.ArtifactVersionMismatchError as exc:
        raise _ARTIFACT_VERSION_MISMATCH_ERROR from exc
    except ai_service.ArtifactNotReadyError as exc:
        raise _ARTIFACT_NOT_READY_ERROR from exc
    return AiArtifactResponse(**result)


@discovery_ai_router.post(
    "/search-drafts", response_model=AiArtifactResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_search_draft(
    payload: SearchDraftCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_search_draft(current.account_id, acting_profile_id, payload.query)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return AiArtifactResponse(**result)


@compatibility_ai_router.post(
    "/{analysis_id}/explanation",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_compatibility_explanation(
    analysis_id: str,
    payload: CompatibilityExplanationCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_compatibility_explanation(
            current.account_id, acting_profile_id, analysis_id
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except compatibility_service.AnalysisNotFoundError as exc:
        raise _ANALYSIS_NOT_FOUND_ERROR from exc
    return AiArtifactResponse(**result)


@conversation_ai_router.post(
    "/{conversation_id}/assistant-drafts",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_assistant_draft(
    conversation_id: str,
    payload: AssistantDraftCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_assistant_draft(
            current.account_id,
            acting_profile_id,
            conversation_id,
            payload.intent,
            payload.tone,
            payload.locale,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    return AiArtifactResponse(**result)


@conversation_ai_router.post(
    "/{conversation_id}/translation-drafts",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_translation_draft(
    conversation_id: str,
    payload: TranslationDraftCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_translation_draft(
            current.account_id,
            acting_profile_id,
            conversation_id,
            payload.target_locale,
            payload.message_id,
            payload.text,
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    except ai_service.TranslationDraftInputError as exc:
        raise _TRANSLATION_DRAFT_INPUT_ERROR from exc
    return AiArtifactResponse(**result)


@conversation_ai_router.post(
    "/{conversation_id}/tone-checks",
    response_model=AiArtifactResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_tone_check(
    conversation_id: str,
    payload: ToneCheckCreateRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.create_tone_check(
            current.account_id, acting_profile_id, conversation_id, payload.text
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except conversations_service.ConversationNotFoundError as exc:
        raise _CONVERSATION_NOT_FOUND_ERROR from exc
    return AiArtifactResponse(**result)


@artifacts_router.get(
    "/{artifact_id}", response_model=AiArtifactResponse, status_code=status.HTTP_200_OK
)
async def get_artifact(
    artifact_id: str,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactResponse:
    try:
        result = ai_service.get_artifact(current.account_id, acting_profile_id, artifact_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except ai_service.ArtifactNotFoundError as exc:
        raise _ARTIFACT_NOT_FOUND_ERROR from exc
    return AiArtifactResponse(**result)


@artifacts_router.post(
    "/{artifact_id}/feedback",
    response_model=AiArtifactFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_feedback(
    artifact_id: str,
    payload: AiArtifactFeedbackRequest,
    acting_profile_id: str = Query(...),
    current: CurrentSession = Depends(get_current_session),
) -> AiArtifactFeedbackResponse:
    try:
        result = ai_service.record_feedback(
            current.account_id, acting_profile_id, artifact_id, payload.rating, payload.category
        )
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    except ai_service.ArtifactNotFoundError as exc:
        raise _ARTIFACT_NOT_FOUND_ERROR from exc
    return AiArtifactFeedbackResponse(**result)
