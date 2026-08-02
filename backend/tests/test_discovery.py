"""Tests for discovery search/profile-view/recommendations/views (catalog §7)."""
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


def _publish_profile(tokens: dict, profile_id: str, *, gender: str, dob: str, community: str) -> None:
    headers = _auth_headers(tokens)
    resp = client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"gender": gender, "date_of_birth": dob},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    resp = client.put(
        f"/v1/profiles/{profile_id}/communities", json={"values": [community]}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/v1/profiles/{profile_id}/submit", headers=headers)
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/v1/profiles/{profile_id}/publish", headers=headers)
    assert resp.status_code == 200, resp.text


def test_search_finds_published_profile_matching_filters(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "disc1@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)

    target_tokens = _register_verify_login(monkeypatch, "disc2@example.com", "correct horse battery")
    target_profile = _create_profile(target_tokens)
    _publish_profile(
        target_tokens, target_profile, gender="female", dob="1995-06-01", community="jatt-sikh"
    )

    resp = client.post(
        "/v1/discovery/search",
        params={"acting_profile_id": seeker_profile},
        json={"filters": {"gender": "female", "min_age": 25, "max_age": 40}},
        headers=_auth_headers(seeker_tokens),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert any(item["profile_id"] == target_profile for item in body["items"])


def test_search_excludes_non_matching_gender(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "disc3@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)

    target_tokens = _register_verify_login(monkeypatch, "disc4@example.com", "correct horse battery")
    target_profile = _create_profile(target_tokens)
    _publish_profile(
        target_tokens, target_profile, gender="male", dob="1990-01-01", community="jatt-sikh"
    )

    resp = client.post(
        "/v1/discovery/search",
        params={"acting_profile_id": seeker_profile},
        json={"filters": {"gender": "female"}},
        headers=_auth_headers(seeker_tokens),
    )
    assert resp.status_code == 200
    assert not any(item["profile_id"] == target_profile for item in resp.json()["items"])


def test_search_rejects_unknown_filter_field(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "disc5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        "/v1/discovery/search",
        params={"acting_profile_id": profile_id},
        json={"filters": {"unknown_field": "x"}},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_get_public_profile_returns_detail_for_published_target(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "disc6@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)

    target_tokens = _register_verify_login(monkeypatch, "disc7@example.com", "correct horse battery")
    target_profile = _create_profile(target_tokens)
    _publish_profile(
        target_tokens, target_profile, gender="female", dob="1992-03-03", community="jatt-sikh"
    )

    resp = client.get(
        f"/v1/discovery/profiles/{target_profile}",
        params={"acting_profile_id": seeker_profile},
        headers=_auth_headers(seeker_tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["profile_id"] == target_profile


def test_get_public_profile_404_for_unpublished_target(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "disc8@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)

    target_tokens = _register_verify_login(monkeypatch, "disc9@example.com", "correct horse battery")
    target_profile = _create_profile(target_tokens)

    resp = client.get(
        f"/v1/discovery/profiles/{target_profile}",
        params={"acting_profile_id": seeker_profile},
        headers=_auth_headers(seeker_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "DISCOVERY_TARGET_PROFILE_NOT_FOUND"


def test_recommendations_returns_published_profiles(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "disc10@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)

    target_tokens = _register_verify_login(monkeypatch, "disc11@example.com", "correct horse battery")
    target_profile = _create_profile(target_tokens)
    _publish_profile(
        target_tokens, target_profile, gender="female", dob="1993-04-04", community="jatt-sikh"
    )

    resp = client.get(
        "/v1/discovery/recommendations",
        params={"acting_profile_id": seeker_profile},
        headers=_auth_headers(seeker_tokens),
    )
    assert resp.status_code == 200
    assert any(item["profile_id"] == target_profile for item in resp.json()["items"])


def test_record_view_is_idempotent_same_day(dynamo_table, monkeypatch):
    seeker_tokens = _register_verify_login(monkeypatch, "disc12@example.com", "correct horse battery")
    seeker_profile = _create_profile(seeker_tokens)
    target_tokens = _register_verify_login(monkeypatch, "disc13@example.com", "correct horse battery")
    target_profile = _create_profile(target_tokens)

    first = client.post(
        "/v1/discovery/views",
        params={"acting_profile_id": seeker_profile},
        json={"target_profile_id": target_profile},
        headers=_auth_headers(seeker_tokens),
    )
    second = client.post(
        "/v1/discovery/views",
        params={"acting_profile_id": seeker_profile},
        json={"target_profile_id": target_profile},
        headers=_auth_headers(seeker_tokens),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["viewed_at"] == second.json()["viewed_at"]


def test_search_requires_auth(dynamo_table):
    resp = client.post(
        "/v1/discovery/search", params={"acting_profile_id": "x"}, json={}
    )
    assert resp.status_code == 401
