"""Tests for generated biodata documents (catalog §6:
`POST /v1/profiles/{profileId}/biodata`, `GET /v1/profiles/{profileId}/biodata/{documentId}`)."""
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


def test_generate_biodata_returns_queued(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bio1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        f"/v1/profiles/{profile_id}/biodata",
        json={"template": "classic", "locale": "en"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["download_url"] is None


def test_get_biodata_returns_document(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bio2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    created = client.post(
        f"/v1/profiles/{profile_id}/biodata",
        json={"template": "classic", "locale": "en"},
        headers=_auth_headers(tokens),
    ).json()

    resp = client.get(
        f"/v1/profiles/{profile_id}/biodata/{created['id']}", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_biodata_unknown_document_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bio3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.get(
        f"/v1/profiles/{profile_id}/biodata/does-not-exist", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_BIODATA_NOT_FOUND"


def test_generate_biodata_requires_auth(dynamo_table):
    resp = client.post(
        "/v1/profiles/some-profile/biodata", json={"template": "classic", "locale": "en"}
    )
    assert resp.status_code == 401
