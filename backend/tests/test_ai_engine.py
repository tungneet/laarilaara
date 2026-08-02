"""Unit tests for the central AI engine (Block 14, `app.core.ai_engine`).

Exercises the `fake` provider paths directly (zero-cost, deterministic) —
the `openai`/`bedrock` code paths are covered by inspection/manual testing
only in this environment (no live API key configured here); see the module
docstring in `app/core/ai_engine.py` for that documented limitation.
"""
from __future__ import annotations

import pytest

from app.core import ai_engine


def test_fake_generate_returns_deterministic_shapes_per_kind():
    bio = ai_engine.generate("profile.bio.draft", {"tone": "warm"})
    assert "bio" in bio

    quality = ai_engine.generate("profile.quality.analysis", {})
    assert "score" in quality and "suggestions" in quality

    extraction = ai_engine.generate("profile.extraction.draft", {"text": "Engineer in Toronto"})
    assert extraction["fields"]["headline"] == "Engineer in Toronto"


def test_fake_generate_unknown_kind_does_not_raise():
    result = ai_engine.generate("some.unknown.kind", {})
    assert "note" in result


def test_fake_moderate_flags_known_keyword():
    result = ai_engine.moderate("I will kill you")
    assert result.flagged is True
    assert result.provider == "fake"
    assert max(result.scores.values()) > 0


def test_fake_moderate_allows_benign_text():
    result = ai_engine.moderate("I enjoy hiking and cooking on weekends.")
    assert result.flagged is False


def test_enforce_moderation_blocks_above_threshold(monkeypatch):
    with pytest.raises(ai_engine.ContentBlockedError):
        ai_engine.enforce_moderation("I will kill you")


def test_enforce_moderation_allows_below_threshold(monkeypatch):
    settings = ai_engine.get_settings()
    monkeypatch.setattr(settings.ai, "moderation_block_threshold", 0.99)
    result = ai_engine.enforce_moderation("I will kill you")
    assert result is not None
    assert result.flagged is True


def test_enforce_moderation_returns_none_for_empty_text():
    assert ai_engine.enforce_moderation(None) is None
    assert ai_engine.enforce_moderation("   ") is None


def test_openai_generate_raises_without_api_key(monkeypatch):
    settings = ai_engine.get_settings()
    monkeypatch.setattr(settings, "openai_api_key", None)
    with pytest.raises(ai_engine.AIProviderNotConfiguredError):
        ai_engine._openai_chat("hello")


def test_openai_moderate_raises_without_api_key(monkeypatch):
    settings = ai_engine.get_settings()
    monkeypatch.setattr(settings, "openai_api_key", None)
    with pytest.raises(ai_engine.AIProviderNotConfiguredError):
        ai_engine._openai_moderate("hello")


def test_enforce_moderation_treats_unconfigured_openai_as_non_blocking(monkeypatch):
    settings = ai_engine.get_settings()
    monkeypatch.setattr(settings.ai, "moderation_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", None)
    # A down/unconfigured moderation provider must not itself block legitimate
    # content — see `enforce_moderation`'s docstring.
    assert ai_engine.enforce_moderation("hello there") is None
