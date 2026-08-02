"""Tests for compatibility analyses (catalog §8:
`POST /v1/compatibility-analyses`, `GET /v1/compatibility-analyses/{analysisId}`)."""
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


def test_create_analysis_then_get_by_id(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "compat1@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "compat2@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    create = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    )
    assert create.status_code == 200
    body = create.json()
    assert body["acting_profile_id"] == a_profile
    assert body["target_profile_id"] == b_profile
    assert 0 <= body["score"] <= 100

    get_resp = client.get(
        f"/v1/compatibility-analyses/{body['id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


def test_create_analysis_is_idempotent_by_pair(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "compat3@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "compat4@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    first = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    )
    second = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    )
    assert first.json()["id"] == second.json()["id"]


def test_get_analysis_owned_by_other_acting_profile_is_404(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "compat5@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "compat6@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)
    c_tokens = _register_verify_login(monkeypatch, "compat7@example.com", "correct horse battery")
    c_profile = _create_profile(c_tokens)

    created = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    ).json()

    resp = client.get(
        f"/v1/compatibility-analyses/{created['id']}",
        params={"acting_profile_id": c_profile},
        headers=_auth_headers(c_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "COMPATIBILITY_ANALYSIS_NOT_FOUND"


def test_compatibility_analyses_require_auth(dynamo_table):
    resp = client.post(
        "/v1/compatibility-analyses",
        params={"acting_profile_id": "x"},
        json={"target_profile_id": "y"},
    )
    assert resp.status_code == 401
