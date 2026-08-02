"""Tests for the private shortlist (catalog §7: `GET /v1/shortlist`,
`PUT/DELETE /v1/shortlist/{targetProfileId}`)."""
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


def test_put_then_list_shortlist(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sl1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    target_tokens = _register_verify_login(monkeypatch, "sl1b@example.com", "correct horse battery")
    target_profile_id = _create_profile(target_tokens)

    put = client.put(
        f"/v1/shortlist/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        json={"note": "Promising match"},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["note"] == "Promising match"

    listing = client.get(
        "/v1/shortlist", params={"acting_profile_id": profile_id}, headers=_auth_headers(tokens)
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_put_shortlist_is_idempotent_and_replaces_note(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sl2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    target_tokens = _register_verify_login(monkeypatch, "sl2b@example.com", "correct horse battery")
    target_profile_id = _create_profile(target_tokens)

    client.put(
        f"/v1/shortlist/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        json={"note": "First"},
        headers=_auth_headers(tokens),
    )
    second = client.put(
        f"/v1/shortlist/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        json={"note": "Updated"},
        headers=_auth_headers(tokens),
    )
    assert second.json()["note"] == "Updated"

    listing = client.get(
        "/v1/shortlist", params={"acting_profile_id": profile_id}, headers=_auth_headers(tokens)
    ).json()
    assert len(listing) == 1


def test_delete_shortlist_is_idempotent(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sl3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    target_tokens = _register_verify_login(monkeypatch, "sl3b@example.com", "correct horse battery")
    target_profile_id = _create_profile(target_tokens)

    client.put(
        f"/v1/shortlist/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        json={},
        headers=_auth_headers(tokens),
    )
    first = client.delete(
        f"/v1/shortlist/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    second = client.delete(
        f"/v1/shortlist/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert first.status_code == 204
    assert second.status_code == 204


def test_shortlist_requires_auth(dynamo_table):
    resp = client.get("/v1/shortlist", params={"acting_profile_id": "x"})
    assert resp.status_code == 401
