"""Tests for /v1/profiles aggregate + lifecycle block (catalog §5, block 1)."""
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


def test_create_self_profile_is_idempotent(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile1@example.com", "correct horse battery")

    first = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    )
    second = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == "draft"
    assert first.json()["version"] == 1


def test_create_other_profile_creates_new_each_time(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile2@example.com", "correct horse battery")

    first = client.post(
        "/v1/profiles", json={"relationship": "other"}, headers=_auth_headers(tokens)
    )
    second = client.post(
        "/v1/profiles", json={"relationship": "other"}, headers=_auth_headers(tokens)
    )
    assert first.json()["id"] != second.json()["id"]


def test_get_and_patch_profile(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile3@example.com", "correct horse battery")
    create_resp = client.post(
        "/v1/profiles", json={"relationship": "self", "locale": "en"}, headers=_auth_headers(tokens)
    )
    profile_id = create_resp.json()["id"]

    get_resp = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens))
    assert get_resp.status_code == 200
    assert get_resp.json()["locale"] == "en"

    patch_resp = client.patch(
        f"/v1/profiles/{profile_id}", json={"locale": "fr"}, headers=_auth_headers(tokens)
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["locale"] == "fr"
    assert patch_resp.json()["version"] == 2


def test_get_unknown_profile_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile4@example.com", "correct horse battery")

    resp = client.get("/v1/profiles/does-not-exist", headers=_auth_headers(tokens))
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_NOT_FOUND"


def test_profile_not_accessible_to_other_accounts(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(
        monkeypatch, "profile5owner@example.com", "correct horse battery"
    )
    other_tokens = _register_verify_login(
        monkeypatch, "profile5other@example.com", "correct horse battery"
    )
    create_resp = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(owner_tokens)
    )
    profile_id = create_resp.json()["id"]

    resp = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(other_tokens))
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_NOT_FOUND"


def test_preview_and_completion_stubs(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile6@example.com", "correct horse battery")
    profile_id = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    ).json()["id"]

    preview = client.get(f"/v1/profiles/{profile_id}/preview", headers=_auth_headers(tokens))
    assert preview.status_code == 200
    assert preview.json()["profile_id"] == profile_id

    completion = client.get(
        f"/v1/profiles/{profile_id}/completion", headers=_auth_headers(tokens)
    )
    assert completion.status_code == 200
    assert completion.json()["score"] == 0
    assert "personal_details" in completion.json()["missing_sections"]

    # Filling a section raises the score and removes it from missing.
    patched = client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"gender": "female", "date_of_birth": "1996-01-15"},
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200

    completion = client.get(
        f"/v1/profiles/{profile_id}/completion", headers=_auth_headers(tokens)
    )
    assert completion.status_code == 200
    body = completion.json()
    assert body["score"] > 0
    assert "personal_details" not in body["missing_sections"]
    assert "narratives" in body["missing_sections"]


def test_full_lifecycle_submit_publish_pause_resume(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile7@example.com", "correct horse battery")
    profile_id = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    ).json()["id"]
    headers = _auth_headers(tokens)

    submit_resp = client.post(f"/v1/profiles/{profile_id}/submit", headers=headers)
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "pending_review"

    publish_resp = client.post(f"/v1/profiles/{profile_id}/publish", headers=headers)
    assert publish_resp.status_code == 200
    assert publish_resp.json()["status"] == "published"

    # Publishing again is idempotent.
    publish_again = client.post(f"/v1/profiles/{profile_id}/publish", headers=headers)
    assert publish_again.status_code == 200
    assert publish_again.json()["status"] == "published"

    pause_resp = client.post(f"/v1/profiles/{profile_id}/pause", headers=headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    resume_resp = client.post(f"/v1/profiles/{profile_id}/resume", headers=headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "published"


def test_cannot_publish_before_submit(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile8@example.com", "correct horse battery")
    profile_id = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    ).json()["id"]

    resp = client.post(f"/v1/profiles/{profile_id}/publish", headers=_auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["code"] == "PROFILE_INVALID_STATE"


def test_cannot_pause_a_draft_profile(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile9@example.com", "correct horse battery")
    profile_id = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    ).json()["id"]

    resp = client.post(f"/v1/profiles/{profile_id}/pause", headers=_auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["code"] == "PROFILE_INVALID_STATE"


def test_delete_profile_starts_deletion_workflow(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "profile10@example.com", "correct horse battery")
    profile_id = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(tokens)
    ).json()["id"]

    resp = client.delete(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens))
    assert resp.status_code == 202
    assert resp.json()["status"] == "deleting"

    # Idempotent: deleting again is a no-op, still 202.
    resp2 = client.delete(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens))
    assert resp2.status_code == 202
    assert resp2.json()["status"] == "deleting"


def test_profiles_require_bearer_token(dynamo_table):
    resp = client.post("/v1/profiles", json={"relationship": "self"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"
