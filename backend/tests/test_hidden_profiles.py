"""Tests for hidden profiles (catalog §7:
`PUT/DELETE /v1/hidden-profiles/{targetProfileId}`), including their effect
on discovery search results."""
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


def _publish_profile(tokens: dict, profile_id: str) -> None:
    headers = _auth_headers(tokens)
    client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"gender": "female", "date_of_birth": "1994-02-02"},
        headers=headers,
    )
    client.post(f"/v1/profiles/{profile_id}/submit", headers=headers)
    client.post(f"/v1/profiles/{profile_id}/publish", headers=headers)


def test_hide_then_unhide_profile(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "hp1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    target_tokens = _register_verify_login(monkeypatch, "hp1b@example.com", "correct horse battery")
    target_profile_id = _create_profile(target_tokens)

    hide = client.put(
        f"/v1/hidden-profiles/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert hide.status_code == 200
    assert hide.json()["target_profile_id"] == target_profile_id

    unhide = client.delete(
        f"/v1/hidden-profiles/{target_profile_id}",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert unhide.status_code == 204


def test_hidden_profile_excluded_from_search(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "hp2@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)
    target_tokens = _register_verify_login(monkeypatch, "hp2b@example.com", "correct horse battery")
    target_profile_id = _create_profile(target_tokens)
    _publish_profile(target_tokens, target_profile_id)

    before = client.get(
        "/v1/discovery/recommendations",
        params={"acting_profile_id": seeker_profile},
        headers=_auth_headers(seeker_tokens),
    )
    assert any(item["profile_id"] == target_profile_id for item in before.json()["items"])

    client.put(
        f"/v1/hidden-profiles/{target_profile_id}",
        params={"acting_profile_id": seeker_profile},
        headers=_auth_headers(seeker_tokens),
    )

    after = client.get(
        "/v1/discovery/recommendations",
        params={"acting_profile_id": seeker_profile},
        headers=_auth_headers(seeker_tokens),
    )
    assert not any(item["profile_id"] == target_profile_id for item in after.json()["items"])


def test_hidden_profiles_require_auth(dynamo_table):
    resp = client.put("/v1/hidden-profiles/target-1", params={"acting_profile_id": "x"})
    assert resp.status_code == 401
