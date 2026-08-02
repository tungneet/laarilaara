"""Tests for the authenticated /v1/me/sessions and /v1/me/consents endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_and_capture_challenge(monkeypatch, email: str, password: str) -> tuple[str, str]:
    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    client.post("/v1/auth/register", json={"email": email, "password": password})
    return captured["challenge_id"], captured["code"]


def _register_verify_login(monkeypatch, email: str, password: str) -> dict:
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)
    client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


def test_list_sessions_shows_current_session(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sessions@example.com", "correct horse battery")

    resp = client.get(
        "/v1/me/sessions", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 1
    assert sessions[0]["is_current"] is True


def test_list_my_profiles_empty_then_lists_created(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "myprofiles@example.com", "correct horse battery")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = client.get("/v1/me/profiles", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []

    created = client.post("/v1/profiles", json={"relationship": "self"}, headers=headers)
    assert created.status_code == 201
    profile_id = created.json()["id"]

    resp = client.get("/v1/me/profiles", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == profile_id
    assert items[0]["my_role"] == "owner"
    assert items[0]["is_primary"] is True
    assert "profile.edit" in items[0]["my_permissions"]

    # Only the manager's own profiles: a second account sees an empty list.
    other = _register_verify_login(monkeypatch, "myprofiles2@example.com", "correct horse battery")
    resp = client.get(
        "/v1/me/profiles", headers={"Authorization": f"Bearer {other['access_token']}"}
    )
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_my_profiles_requires_auth(dynamo_table):
    resp = client.get("/v1/me/profiles")
    assert resp.status_code == 401


def test_list_sessions_reflects_multiple_logins(dynamo_table, monkeypatch):
    email, password = "multisession@example.com", "correct horse battery"
    tokens_a = _register_verify_login(monkeypatch, email, password)
    login_b = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login_b.status_code == 200

    resp = client.get(
        "/v1/me/sessions", headers={"Authorization": f"Bearer {tokens_a['access_token']}"}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_revoke_session_by_id(dynamo_table, monkeypatch):
    email, password = "revokeone@example.com", "correct horse battery"
    tokens = _register_verify_login(monkeypatch, email, password)

    sessions = client.get(
        "/v1/me/sessions", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    ).json()
    session_id = sessions[0]["id"]

    resp = client.delete(
        f"/v1/me/sessions/{session_id}",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 204

    # The revoked session's refresh token can no longer be used.
    refresh_resp = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 401


def test_revoke_unknown_session_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "revoke404@example.com", "correct horse battery")

    resp = client.delete(
        "/v1/me/sessions/does-not-exist",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SESSION_NOT_FOUND"


def test_sessions_require_bearer_token(dynamo_table):
    resp = client.get("/v1/me/sessions")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_record_and_read_consents(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "consents@example.com", "correct horse battery")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = client.post(
        "/v1/me/consents",
        json={"consent_type": "marketing", "granted": True, "policy_version": "2026-01"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["granted"] is True

    resp2 = client.post(
        "/v1/me/consents",
        json={"consent_type": "marketing", "granted": False, "policy_version": "2026-02"},
        headers=headers,
    )
    assert resp2.status_code == 201

    summary = client.get("/v1/me/consents", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    # Latest decision wins in "current"; both decisions are kept in history.
    assert body["current"]["marketing"]["granted"] is False
    assert body["current"]["marketing"]["policy_version"] == "2026-02"
    assert len(body["history"]) == 2


def test_consents_require_bearer_token(dynamo_table):
    resp = client.get("/v1/me/consents")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"
