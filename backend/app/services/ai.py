"""Service layer for catalog §10 "AI-assisted domain endpoints".

Every generation endpoint here (`extraction-drafts`, `bio-drafts`,
`quality-analyses`, `search-drafts`, `explanation`, `assistant-drafts`,
`translation-drafts`, `tone-checks`) creates a single `AiArtifact` row (see
`app/repositories/ai_artifacts.py`) that doubles as the catalog's shared
`Operation` resource, then IMMEDIATELY runs it through the central
`app.core.ai_engine` (Block 14) and transitions it to `succeeded`/`failed` —
synchronously, inline, since no SQS/EventBridge worker exists anywhere in
this codebase. This closes what used to be a permanent "queued forever" gap.

REMAINING GAPS (documented):
- `apply_artifact` can now actually reach `succeeded` and return 200, but it
  still does not automatically merge the generated draft back into profile
  fields — the caller (frontend) is expected to review and copy accepted
  suggestions into the relevant section form. Auto-merge is a larger,
  separate change (would need per-kind field-mapping logic) and is left for
  later.
- `tone-checks` stays a queued-then-immediately-completed artifact rather
  than using the catalog's alternate "bounded synchronous mode" option, for
  consistency with every other endpoint in this batch — the practical
  difference is now negligible since completion is synchronous either way.
- Content-moderation ( `app.core.ai_engine.enforce_moderation` ) is wired
  into messages (`app.services.conversations`) and profile narratives
  (`app.services.profile_sections`), but NOT into these AI-generation
  endpoints' own free-text inputs (extraction/search/translation/tone text)
  or into reports — flagged as a follow-up, same class of gap as before.
"""
from __future__ import annotations

from app.core import ai_engine
from app.repositories import ai_artifacts as artifacts_repo
from app.services import compatibility as compatibility_service
from app.services import conversations as conversations_service
from app.services import profiles as profiles_service


class ArtifactNotFoundError(Exception):
    pass


class ArtifactNotReadyError(Exception):
    pass


class ArtifactVersionMismatchError(Exception):
    pass


class TranslationDraftInputError(Exception):
    pass


def _get_owned_artifact_or_404(acting_profile_id: str, artifact_id: str) -> dict:
    artifact = artifacts_repo.get_artifact(artifact_id)
    if artifact is None or artifact["owner_profile_id"] != acting_profile_id:
        # Mask existence: an artifact owned by a different acting profile
        # looks identical to one that doesn't exist.
        raise ArtifactNotFoundError(artifact_id)
    return artifact


def _run_and_complete(artifact: dict) -> dict:
    """Run `artifact` through the central AI engine and transition it to
    `succeeded`/`failed`. A provider failure (missing API key, network error,
    unreachable endpoint) fails the artifact rather than the HTTP request —
    callers still get a 202/201 response and can inspect `error` via GET.
    """
    try:
        result = ai_engine.generate(artifact["kind"], artifact["input"])
    except Exception as exc:  # noqa: BLE001 - provider failures are data, not 500s
        return artifacts_repo.mark_failed(artifact_id=artifact["id"], error={"message": str(exc)})
    return artifacts_repo.mark_succeeded(artifact_id=artifact["id"], result=result)


# ---------------------------------------------------------------------------
# Profile-scoped: extraction-drafts, bio-drafts, quality-analyses, apply
# ---------------------------------------------------------------------------


def create_extraction_draft(account_id: str, acting_profile_id: str, text: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profile = profiles_service.get_or_404(acting_profile_id)

    subject = {"type": "profile", "id": acting_profile_id, "version": profile.version}
    artifact = artifacts_repo.create_artifact(
        "profile.extraction.draft", acting_profile_id, subject, {"text": text}
    )
    return _run_and_complete(artifact)


def create_bio_draft(account_id: str, acting_profile_id: str, tone: str | None) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profile = profiles_service.get_or_404(acting_profile_id)

    subject = {"type": "profile", "id": acting_profile_id, "version": profile.version}
    artifact = artifacts_repo.create_artifact(
        "profile.bio.draft", acting_profile_id, subject, {"tone": tone}
    )
    return _run_and_complete(artifact)


def create_quality_analysis(account_id: str, acting_profile_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profile = profiles_service.get_or_404(acting_profile_id)

    subject = {"type": "profile", "id": acting_profile_id, "version": profile.version}
    artifact = artifacts_repo.create_artifact(
        "profile.quality.analysis", acting_profile_id, subject, {}
    )
    return _run_and_complete(artifact)


def apply_artifact(
    account_id: str,
    acting_profile_id: str,
    artifact_id: str,
    expected_profile_version: int,
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profile = profiles_service.get_or_404(acting_profile_id)

    artifact = _get_owned_artifact_or_404(acting_profile_id, artifact_id)
    if profile.version != expected_profile_version:
        raise ArtifactVersionMismatchError(expected_profile_version)
    if artifact["status"] != "succeeded":
        # Reachable now that generation runs synchronously: a `failed`
        # artifact (e.g. a misconfigured/unreachable provider) still 409s here.
        raise ArtifactNotReadyError(artifact_id)
    return artifact


# ---------------------------------------------------------------------------
# Discovery-scoped: search-drafts
# ---------------------------------------------------------------------------


def create_search_draft(account_id: str, acting_profile_id: str, query: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    subject = {"type": "discovery", "id": acting_profile_id, "version": None}
    artifact = artifacts_repo.create_artifact(
        "discovery.search.draft", acting_profile_id, subject, {"query": query}
    )
    return _run_and_complete(artifact)


# ---------------------------------------------------------------------------
# Compatibility-scoped: explanation
# ---------------------------------------------------------------------------


def create_compatibility_explanation(
    account_id: str, acting_profile_id: str, analysis_id: str
) -> dict:
    # Reuses compatibility_service's existence-masking ownership check so a
    # non-owning acting profile sees the identical 404 as a missing analysis.
    analysis = compatibility_service.get_analysis(account_id, acting_profile_id, analysis_id)

    subject = {"type": "compatibility_analysis", "id": analysis["id"], "version": None}
    artifact = artifacts_repo.create_artifact(
        "compatibility.explanation", acting_profile_id, subject, {}
    )
    return _run_and_complete(artifact)


# ---------------------------------------------------------------------------
# Conversation-scoped: assistant-drafts, translation-drafts, tone-checks
# ---------------------------------------------------------------------------


def create_assistant_draft(
    account_id: str,
    acting_profile_id: str,
    conversation_id: str,
    intent: str,
    tone: str | None,
    locale: str | None,
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)
    conversations_service.get_conversation_for_participant(acting_profile_id, conversation_id)

    subject = {"type": "conversation", "id": conversation_id, "version": None}
    artifact = artifacts_repo.create_artifact(
        "conversation.assistant.draft",
        acting_profile_id,
        subject,
        {"intent": intent, "tone": tone, "locale": locale},
    )
    return _run_and_complete(artifact)


def create_translation_draft(
    account_id: str,
    acting_profile_id: str,
    conversation_id: str,
    target_locale: str,
    message_id: str | None,
    text: str | None,
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)
    conversations_service.get_conversation_for_participant(acting_profile_id, conversation_id)

    if not message_id and not text:
        raise TranslationDraftInputError()

    subject = {"type": "conversation", "id": conversation_id, "version": None}
    artifact = artifacts_repo.create_artifact(
        "conversation.translation.draft",
        acting_profile_id,
        subject,
        {"target_locale": target_locale, "message_id": message_id, "text": text},
    )
    return _run_and_complete(artifact)


def create_tone_check(
    account_id: str, acting_profile_id: str, conversation_id: str, text: str
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)
    conversations_service.get_conversation_for_participant(acting_profile_id, conversation_id)

    subject = {"type": "conversation", "id": conversation_id, "version": None}
    artifact = artifacts_repo.create_artifact(
        "conversation.tone.check", acting_profile_id, subject, {"text": text}
    )
    return _run_and_complete(artifact)


# ---------------------------------------------------------------------------
# Generic artifact access: get, feedback
# ---------------------------------------------------------------------------


def get_artifact(account_id: str, acting_profile_id: str, artifact_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    return _get_owned_artifact_or_404(acting_profile_id, artifact_id)


def record_feedback(
    account_id: str,
    acting_profile_id: str,
    artifact_id: str,
    rating: int,
    category: str | None,
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    _get_owned_artifact_or_404(acting_profile_id, artifact_id)
    return artifacts_repo.put_feedback(artifact_id, acting_profile_id, rating, category)
