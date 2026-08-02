"""Tests for saved searches (catalog §7: `GET/POST /v1/saved-searches`,
`PATCH/DELETE /v1/saved-searches/{searchId}`)."""
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


def test_create_then_list_saved_search(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ss1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    create = client.post(
        "/v1/saved-searches",
        params={"acting_profile_id": profile_id},
        json={"name": "My search", "filters": {"gender": "female"}, "alert": True},
        headers=_auth_headers(tokens),
    )
    assert create.status_code == 201
    assert create.json()["name"] == "My search"

    listing = client.get(
        "/v1/saved-searches", params={"acting_profile_id": profile_id}, headers=_auth_headers(tokens)
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_create_saved_search_is_idempotent_by_name(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ss2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    first = client.post(
        "/v1/saved-searches",
        params={"acting_profile_id": profile_id},
        json={"name": "Dup search"},
        headers=_auth_headers(tokens),
    )
    second = client.post(
        "/v1/saved-searches",
        params={"acting_profile_id": profile_id},
        json={"name": "Dup search"},
        headers=_auth_headers(tokens),
    )
    assert first.json()["id"] == second.json()["id"]


def test_patch_and_delete_saved_search(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ss3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    created = client.post(
        "/v1/saved-searches",
        params={"acting_profile_id": profile_id},
        json={"name": "Original"},
        headers=_auth_headers(tokens),
    ).json()

    patched = client.patch(
        f"/v1/saved-searches/{created['id']}",
        params={"acting_profile_id": profile_id},
        json={"name": "Renamed"},
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Renamed"

    deleted = client.delete(
        f"/v1/saved-searches/{created['id']}",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert deleted.status_code == 204

    listing = client.get(
        "/v1/saved-searches", params={"acting_profile_id": profile_id}, headers=_auth_headers(tokens)
    )
    assert listing.json() == []


def test_patch_unknown_saved_search_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "ss4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        "/v1/saved-searches/does-not-exist",
        params={"acting_profile_id": profile_id},
        json={"name": "X"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SAVED_SEARCH_NOT_FOUND"


def test_saved_searches_require_auth(dynamo_table):
    resp = client.get("/v1/saved-searches", params={"acting_profile_id": "x"})
    assert resp.status_code == 401
