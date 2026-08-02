"""Central AI engine (Block 14): a single seam every AI-assisted capability
in the codebase calls through, regardless of which underlying model channel
is configured (`settings.ai.provider`: fake | openai | bedrock) — mirrors the
one-seam pattern already used by `app.services.entitlements`.

Two capabilities:

- `generate(kind, payload)` — text/structured generation for the catalog §10
  AI-assisted endpoints (bio drafts, quality analyses, translations, tone
  checks, etc.). Runs SYNCHRONOUSLY inline, because no SQS/EventBridge worker
  exists anywhere in this codebase — this is what lets artifacts reach
  `succeeded`/`failed` immediately instead of staying `queued` forever (a
  previously-documented gap; see `app.services.ai`).
- `moderate(text)` / `enforce_moderation(text)` — content-safety scanning.
  Selected independently via `settings.ai.moderation_provider`, so moderation
  can run on OpenAI's real omni-moderation model even while text generation
  stays on the free `fake` provider. Used as a synchronous safety gate before
  messages are sent and before profile narratives are saved (see
  `app.services.conversations` / `app.services.profile_sections`).

Provider notes:
- `fake` providers are fully deterministic, zero-cost, and are what the test
  suite / local dev exercise by default (`ai.provider`/`ai.moderation_provider`
  both default to `"fake"`).
- `openai` providers make real HTTP calls to the OpenAI API using
  `settings.openai_api_key`. If that key is unset, calls raise
  `AIProviderNotConfiguredError` rather than silently falling back, so a
  misconfiguration is loud instead of masked.
- `bedrock` is a best-effort `boto3` `bedrock-runtime` integration, included
  for completeness (the product wants "various channels: Bedrock/API-based
  etc."). It is structurally complete but NOT exercised by the test suite in
  this environment (no AWS Bedrock access here) — treat as unverified until
  run against real Bedrock credentials.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIProviderNotConfiguredError(Exception):
    """A real provider is selected but has no usable credentials."""


class ContentBlockedError(Exception):
    """Raised when moderation flags text at/above the configured threshold."""

    def __init__(self, moderation: "ModerationResult") -> None:
        super().__init__("content blocked by moderation")
        self.moderation = moderation


@dataclass
class ModerationResult:
    flagged: bool
    categories: dict[str, bool] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    provider: str = "fake"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

_FAKE_TEMPLATES = {
    "profile.extraction.draft": lambda payload: {
        "fields": {"headline": (payload.get("text") or "").strip()[:80]},
        "note": "Fake extraction — set ai.provider=openai (with an API key) for real parsing.",
    },
    "profile.bio.draft": lambda payload: {
        "bio": (
            f"A thoughtful, {payload.get('tone') or 'genuine'} person looking to build a "
            "meaningful partnership rooted in shared values and mutual respect."
        ),
    },
    "profile.quality.analysis": lambda payload: {
        "score": 62,
        "suggestions": [
            "Add more detail to your bio.",
            "Complete your lifestyle section for better matches.",
        ],
    },
    "discovery.search.draft": lambda payload: {
        "filters": {"free_text": payload.get("query", "")},
        "note": "Fake search interpretation — no real NLP parsing applied.",
    },
    "compatibility.explanation": lambda payload: {
        "summary": "Compatibility is driven by shared community, age range, and lifestyle overlap.",
    },
    "conversation.assistant.draft": lambda payload: {
        "draft": f"Thanks for your message! (auto-drafted, intent={payload.get('intent')})",
    },
    "conversation.translation.draft": lambda payload: {
        "translated_text": payload.get("text") or "",
        "target_locale": payload.get("target_locale"),
        "note": "Fake passthrough translation — set ai.provider=openai for a real one.",
    },
    "conversation.tone.check": lambda payload: {
        "tone": "neutral",
        "suggestions": [],
    },
}


def _fake_generate(kind: str, payload: dict) -> dict:
    template = _FAKE_TEMPLATES.get(kind)
    return template(payload) if template else {"note": f"no fake template for kind={kind}"}


_OPENAI_PROMPTS = {
    "profile.extraction.draft": lambda payload: (
        "Extract matrimony profile fields (headline, occupation, education, city) as compact "
        f"JSON from this free text: {payload.get('text')}"
    ),
    "profile.bio.draft": lambda payload: (
        "Write a warm, honest, 3-sentence matrimony profile bio in a "
        f"{payload.get('tone') or 'genuine'} tone."
    ),
    "profile.quality.analysis": lambda payload: (
        "Give a 0-100 completeness/quality score and up to 3 improvement suggestions for a "
        "matrimony profile, as JSON with keys score and suggestions."
    ),
    "discovery.search.draft": lambda payload: (
        f"Convert this free-text partner search into structured filters as JSON: {payload.get('query')}"
    ),
    "compatibility.explanation": lambda payload: (
        "Explain in 2-3 sentences why two matrimony profiles might be compatible."
    ),
    "conversation.assistant.draft": lambda payload: (
        f"Draft a short, respectful chat reply. Intent={payload.get('intent')}, tone={payload.get('tone')}."
    ),
    "conversation.translation.draft": lambda payload: (
        f"Translate the following text to {payload.get('target_locale')}: {payload.get('text')}"
    ),
    "conversation.tone.check": lambda payload: (
        f"Assess the tone of this message and suggest improvements if needed: {payload.get('text')}"
    ),
}


def _openai_chat(prompt: str, json_mode: bool = False) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise AIProviderNotConfiguredError("ai.provider=openai but no openai_api_key is set")
    base_url = (settings.ai.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    body: dict = {
        "model": settings.ai.openai_chat_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json=body,
        timeout=settings.ai.request_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# Kinds whose OpenAI prompt asks for a JSON object response (see
# `_OPENAI_PROMPTS`) — matched against each kind's expected structured result
# shape (same keys the `fake` provider's templates use), so the frontend can
# read `result.score`/`result.bio`/etc. the same way regardless of provider.
_JSON_RESULT_KINDS = {
    "profile.extraction.draft",
    "profile.quality.analysis",
    "discovery.search.draft",
    "conversation.tone.check",
}

# Kinds whose OpenAI prompt returns plain prose, wrapped under the same key
# the `fake` provider uses for that kind.
_TEXT_RESULT_KEY = {
    "profile.bio.draft": "bio",
    "compatibility.explanation": "summary",
    "conversation.assistant.draft": "draft",
}


def _openai_generate(kind: str, payload: dict) -> dict:
    prompt_builder = _OPENAI_PROMPTS.get(kind)
    if prompt_builder is None:
        return _fake_generate(kind, payload)

    if kind in _JSON_RESULT_KINDS:
        raw = _openai_chat(prompt_builder(payload) + " Respond with a JSON object only.", json_mode=True)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        # Model didn't return valid JSON: fall back to the fake template's
        # shape (so the frontend contract still holds) but keep the raw text.
        fallback = _fake_generate(kind, payload)
        fallback["raw_text"] = raw
        return fallback

    raw = _openai_chat(prompt_builder(payload))
    if kind == "conversation.translation.draft":
        return {"translated_text": raw, "target_locale": payload.get("target_locale")}
    key = _TEXT_RESULT_KEY.get(kind, "text")
    return {key: raw}


def _bedrock_generate(kind: str, payload: dict) -> dict:
    """Best-effort Bedrock channel. Structurally complete; NOT exercised by
    the test suite in this environment (no AWS Bedrock access here)."""
    import boto3  # local import: keep boto3 optional for the non-bedrock path

    settings = get_settings()
    prompt_builder = _OPENAI_PROMPTS.get(kind)  # same prompt text works across providers
    if prompt_builder is None:
        return _fake_generate(kind, payload)

    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt_builder(payload)}],
        }
    )
    response = client.invoke_model(modelId=settings.ai.chat_model, body=body)
    parsed = json.loads(response["body"].read())
    raw = parsed["content"][0]["text"]

    # Normalize to the same per-kind result shape as `_openai_generate` /
    # the `fake` templates, so the frontend contract holds across providers.
    if kind in _JSON_RESULT_KINDS:
        try:
            parsed_json = json.loads(raw)
            if isinstance(parsed_json, dict):
                return parsed_json
        except (json.JSONDecodeError, TypeError):
            pass
        fallback = _fake_generate(kind, payload)
        fallback["raw_text"] = raw
        return fallback
    if kind == "conversation.translation.draft":
        return {"translated_text": raw, "target_locale": payload.get("target_locale")}
    key = _TEXT_RESULT_KEY.get(kind, "text")
    return {key: raw}


def generate(kind: str, payload: dict) -> dict:
    settings = get_settings()
    if settings.ai.provider == "openai":
        return _openai_generate(kind, payload)
    if settings.ai.provider == "bedrock":
        return _bedrock_generate(kind, payload)
    return _fake_generate(kind, payload)


# ---------------------------------------------------------------------------
# Moderation
# ---------------------------------------------------------------------------

# Small representative list so the zero-cost `fake` moderation provider can
# still demonstrate/test the blocking path without any external call.
_FAKE_FLAGGED_KEYWORDS = {"kill", "suicide", "rape", "terrorist", "nazi"}


def _fake_moderate(text: str) -> ModerationResult:
    lowered = text.lower()
    hit = next((word for word in _FAKE_FLAGGED_KEYWORDS if word in lowered), None)
    if hit is None:
        return ModerationResult(flagged=False, provider="fake")
    return ModerationResult(
        flagged=True,
        categories={"violence": True},
        scores={"violence": 0.9},
        provider="fake",
    )


def _openai_moderate(text: str) -> ModerationResult:
    settings = get_settings()
    if not settings.openai_api_key:
        raise AIProviderNotConfiguredError(
            "ai.moderation_provider=openai but no openai_api_key is set"
        )
    base_url = (settings.ai.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    response = httpx.post(
        f"{base_url}/moderations",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": "omni-moderation-latest", "input": text},
        timeout=settings.ai.request_timeout_seconds,
    )
    response.raise_for_status()
    result = response.json()["results"][0]
    return ModerationResult(
        flagged=result["flagged"],
        categories=result["categories"],
        scores=result["category_scores"],
        provider="openai",
    )


def moderate(text: str) -> ModerationResult:
    if not text or not text.strip():
        return ModerationResult(flagged=False)
    settings = get_settings()
    if settings.ai.moderation_provider == "openai":
        return _openai_moderate(text)
    return _fake_moderate(text)


def enforce_moderation(text: str | None) -> ModerationResult | None:
    """Moderate `text` and raise `ContentBlockedError` if flagged content is
    at/above `ai.moderation_block_threshold`. Returns the (non-blocking)
    result otherwise, or `None` if there was no text to check.

    Moderation-provider failures (e.g. the OpenAI API being unreachable) are
    logged and treated as non-blocking rather than failing the write — a
    down moderation provider should not itself become a denial-of-service
    vector against legitimate users.
    """
    if not text or not text.strip():
        return None
    try:
        result = moderate(text)
    except (AIProviderNotConfiguredError, httpx.HTTPError) as exc:
        logger.warning("moderation check failed, allowing content through: %s", exc)
        return None
    if not result.flagged:
        return result
    highest = max(result.scores.values()) if result.scores else 1.0
    settings = get_settings()
    if highest >= settings.ai.moderation_block_threshold:
        raise ContentBlockedError(result)
    return result
