"""Tests for catalog §10 "AI-assisted domain endpoints" (11 HTTP operations).

Generation now runs SYNCHRONOUSLY through the central `app.core.ai_engine`
(Block 14, fake provider by default) immediately after artifact creation, so
artifacts reach `succeeded` (or `failed`, on a provider error) right away
instead of staying `queued` forever.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_verify_login(monkeypatch, email: str, password: str) -> dict:
    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    client.post("/v1/auth/register", json={"email": email, "password": password})
    client.post(
        f"/v1/auth/challenges/{captured['challenge_id']}/verify",
        json={"code": captured["code"]},
    )
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_profile(tokens: dict) -> str:
    resp = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    )
    return resp.json()["id"]


def _create_conversation(monkeypatch, email_a: str, email_b: str) -> tuple[dict, str, dict, str, str]:
    a_tokens = _register_verify_login(monkeypatch, email_a, "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, email_b, "correct horse battery")
    b_profile = _create_profile(b_tokens)

    sent = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    ).json()
    accepted = client.post(
        f"/v1/interests/{sent['id']}/accept",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    ).json()
    match_resp = client.get(
        f"/v1/matches/{accepted['match_id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    ).json()
    return a_tokens, a_profile, b_tokens, b_profile, match_resp["conversation_id"]


def test_extraction_draft_succeeds(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        f"/v1/profiles/{profile_id}/ai/extraction-drafts",
        json={"text": "I am a software engineer living in Toronto."},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "succeeded"
    assert body["kind"] == "profile.extraction.draft"
    assert body["subject"]["type"] == "profile"
    assert body["subject"]["id"] == profile_id
    assert body["result"] is not None


def test_bio_draft_succeeds(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        f"/v1/profiles/{profile_id}/ai/bio-drafts",
        json={"tone": "warm"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["kind"] == "profile.bio.draft"
    assert body["status"] == "succeeded"
    assert "bio" in body["result"]


def test_quality_analysis_succeeds(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        f"/v1/profiles/{profile_id}/ai/quality-analyses",
        json={},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["kind"] == "profile.quality.analysis"
    assert body["status"] == "succeeded"
    assert "score" in body["result"]


def test_apply_artifact_not_ready_when_generation_fails(dynamo_table, monkeypatch):
    monkeypatch.setattr(
        "app.core.ai_engine.generate",
        lambda kind, payload: (_ for _ in ()).throw(RuntimeError("provider unreachable")),
    )
    tokens = _register_verify_login(monkeypatch, "ai4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    draft = client.post(
        f"/v1/profiles/{profile_id}/ai/bio-drafts",
        json={},
        headers=_auth_headers(tokens),
    ).json()
    assert draft["status"] == "failed"

    resp = client.post(
        f"/v1/profiles/{profile_id}/ai-artifacts/{draft['id']}/apply",
        json={"expected_profile_version": 1},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "AI_ARTIFACT_NOT_READY"


def test_apply_artifact_succeeds_when_ready(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai4b@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    draft = client.post(
        f"/v1/profiles/{profile_id}/ai/bio-drafts",
        json={},
        headers=_auth_headers(tokens),
    ).json()
    assert draft["status"] == "succeeded"

    resp = client.post(
        f"/v1/profiles/{profile_id}/ai-artifacts/{draft['id']}/apply",
        json={"expected_profile_version": 1},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["result"] is not None


def test_apply_artifact_version_mismatch(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    draft = client.post(
        f"/v1/profiles/{profile_id}/ai/bio-drafts",
        json={},
        headers=_auth_headers(tokens),
    ).json()

    resp = client.post(
        f"/v1/profiles/{profile_id}/ai-artifacts/{draft['id']}/apply",
        json={"expected_profile_version": 999},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "AI_ARTIFACT_VERSION_MISMATCH"


def test_apply_artifact_not_owned_is_404(dynamo_table, monkeypatch):
    tokens_a = _register_verify_login(monkeypatch, "ai6a@example.com", "correct horse battery")
    profile_a = _create_profile(tokens_a)
    tokens_b = _register_verify_login(monkeypatch, "ai6b@example.com", "correct horse battery")
    profile_b = _create_profile(tokens_b)

    draft = client.post(
        f"/v1/profiles/{profile_a}/ai/bio-drafts",
        json={},
        headers=_auth_headers(tokens_a),
    ).json()

    resp = client.post(
        f"/v1/profiles/{profile_b}/ai-artifacts/{draft['id']}/apply",
        json={"expected_profile_version": 1},
        headers=_auth_headers(tokens_b),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "AI_ARTIFACT_NOT_FOUND"


def test_search_draft_is_queued(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai7@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        "/v1/discovery/search-drafts",
        params={"acting_profile_id": profile_id},
        json={"query": "tall punjabi engineer in toronto"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["kind"] == "discovery.search.draft"
    assert body["subject"]["type"] == "discovery"


def test_compatibility_explanation_is_queued(dynamo_table, monkeypatch):
    tokens_a = _register_verify_login(monkeypatch, "ai8a@example.com", "correct horse battery")
    profile_a = _create_profile(tokens_a)
    tokens_b = _register_verify_login(monkeypatch, "ai8b@example.com", "correct horse battery")
    profile_b = _create_profile(tokens_b)

    analysis = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": profile_a},
        json={"target_profile_id": profile_b},
        headers=_auth_headers(tokens_a),
    ).json()

    resp = client.post(
        f"/v1/compatibility-analyses/{analysis['id']}/explanation",
        params={"acting_profile_id": profile_a},
        json={},
        headers=_auth_headers(tokens_a),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["kind"] == "compatibility.explanation"
    assert body["subject"]["id"] == analysis["id"]


def test_compatibility_explanation_wrong_owner_is_404(dynamo_table, monkeypatch):
    tokens_a = _register_verify_login(monkeypatch, "ai9a@example.com", "correct horse battery")
    profile_a = _create_profile(tokens_a)
    tokens_b = _register_verify_login(monkeypatch, "ai9b@example.com", "correct horse battery")
    profile_b = _create_profile(tokens_b)

    analysis = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": profile_a},
        json={"target_profile_id": profile_b},
        headers=_auth_headers(tokens_a),
    ).json()

    resp = client.post(
        f"/v1/compatibility-analyses/{analysis['id']}/explanation",
        params={"acting_profile_id": profile_b},
        json={},
        headers=_auth_headers(tokens_b),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "COMPATIBILITY_ANALYSIS_NOT_FOUND"


def test_assistant_draft_is_queued(dynamo_table, monkeypatch):
    a_tokens, a_profile, _b_tokens, _b_profile, conversation_id = _create_conversation(
        monkeypatch, "ai10a@example.com", "ai10b@example.com"
    )

    resp = client.post(
        f"/v1/conversations/{conversation_id}/assistant-drafts",
        params={"acting_profile_id": a_profile},
        json={"intent": "reply", "tone": "friendly", "locale": "en"},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["kind"] == "conversation.assistant.draft"
    assert body["subject"]["id"] == conversation_id


def test_translation_draft_requires_message_id_or_text(dynamo_table, monkeypatch):
    a_tokens, a_profile, _b_tokens, _b_profile, conversation_id = _create_conversation(
        monkeypatch, "ai11a@example.com", "ai11b@example.com"
    )

    resp = client.post(
        f"/v1/conversations/{conversation_id}/translation-drafts",
        params={"acting_profile_id": a_profile},
        json={"target_locale": "fr"},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "TRANSLATION_DRAFT_INPUT_REQUIRED"

    ok_resp = client.post(
        f"/v1/conversations/{conversation_id}/translation-drafts",
        params={"acting_profile_id": a_profile},
        json={"target_locale": "fr", "text": "hello"},
        headers=_auth_headers(a_tokens),
    )
    assert ok_resp.status_code == 202
    assert ok_resp.json()["kind"] == "conversation.translation.draft"


def test_tone_check_non_participant_is_404(dynamo_table, monkeypatch):
    _a_tokens, _a_profile, _b_tokens, _b_profile, conversation_id = _create_conversation(
        monkeypatch, "ai12a@example.com", "ai12b@example.com"
    )
    outsider_tokens = _register_verify_login(monkeypatch, "ai12c@example.com", "correct horse battery")
    outsider_profile = _create_profile(outsider_tokens)

    resp = client.post(
        f"/v1/conversations/{conversation_id}/tone-checks",
        params={"acting_profile_id": outsider_profile},
        json={"text": "hey there"},
        headers=_auth_headers(outsider_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "CONVERSATION_NOT_FOUND"


def test_get_artifact_and_feedback(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ai13@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    draft = client.post(
        f"/v1/profiles/{profile_id}/ai/bio-drafts",
        json={},
        headers=_auth_headers(tokens),
    ).json()

    get_resp = client.get(
        f"/v1/ai-artifacts/{draft['id']}",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == draft["id"]

    feedback_resp = client.post(
        f"/v1/ai-artifacts/{draft['id']}/feedback",
        params={"acting_profile_id": profile_id},
        json={"rating": 4, "category": "helpful"},
        headers=_auth_headers(tokens),
    )
    assert feedback_resp.status_code == 201
    assert feedback_resp.json()["rating"] == 4

    # Idempotent: resubmitting feedback overwrites rather than erroring.
    feedback_resp2 = client.post(
        f"/v1/ai-artifacts/{draft['id']}/feedback",
        params={"acting_profile_id": profile_id},
        json={"rating": 2, "category": None},
        headers=_auth_headers(tokens),
    )
    assert feedback_resp2.status_code == 201
    assert feedback_resp2.json()["rating"] == 2


def test_get_artifact_not_owned_is_404(dynamo_table, monkeypatch):
    tokens_a = _register_verify_login(monkeypatch, "ai14a@example.com", "correct horse battery")
    profile_a = _create_profile(tokens_a)
    tokens_b = _register_verify_login(monkeypatch, "ai14b@example.com", "correct horse battery")
    profile_b = _create_profile(tokens_b)

    draft = client.post(
        f"/v1/profiles/{profile_a}/ai/bio-drafts",
        json={},
        headers=_auth_headers(tokens_a),
    ).json()

    resp = client.get(
        f"/v1/ai-artifacts/{draft['id']}",
        params={"acting_profile_id": profile_b},
        headers=_auth_headers(tokens_b),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "AI_ARTIFACT_NOT_FOUND"


def test_ai_endpoints_require_auth(dynamo_table):
    resp = client.post(
        "/v1/discovery/search-drafts",
        params={"acting_profile_id": "whatever"},
        json={"query": "test"},
    )
    assert resp.status_code == 401
