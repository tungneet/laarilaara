"""Tests for matches (catalog §8: `GET /v1/matches`, `GET /v1/matches/{matchId}`,
`POST /v1/matches/{matchId}/end|feedback|outcomes`)."""
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


def _create_match(monkeypatch, email_a: str, email_b: str) -> tuple[dict, str, dict, str, str]:
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
    return a_tokens, a_profile, b_tokens, b_profile, accepted["match_id"]


def test_list_matches_for_both_participants(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, match_id = _create_match(
        monkeypatch, "match1@example.com", "match2@example.com"
    )

    a_list = client.get(
        "/v1/matches", params={"acting_profile_id": a_profile}, headers=_auth_headers(a_tokens)
    )
    b_list = client.get(
        "/v1/matches", params={"acting_profile_id": b_profile}, headers=_auth_headers(b_tokens)
    )
    assert a_list.status_code == 200
    assert b_list.status_code == 200
    assert any(item["id"] == match_id for item in a_list.json()["items"])
    assert any(item["id"] == match_id for item in b_list.json()["items"])


def test_get_match_for_non_participant_is_404(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, match_id = _create_match(
        monkeypatch, "match3@example.com", "match4@example.com"
    )
    c_tokens = _register_verify_login(monkeypatch, "match5@example.com", "correct horse battery")
    c_profile = _create_profile(c_tokens)

    resp = client.get(
        f"/v1/matches/{match_id}",
        params={"acting_profile_id": c_profile},
        headers=_auth_headers(c_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "MATCH_NOT_FOUND"


def test_end_match_is_idempotent(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, match_id = _create_match(
        monkeypatch, "match6@example.com", "match7@example.com"
    )

    first = client.post(
        f"/v1/matches/{match_id}/end",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    second = client.post(
        f"/v1/matches/{match_id}/end",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "ended"
    assert second.json()["status"] == "ended"


def test_submit_feedback(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, match_id = _create_match(
        monkeypatch, "match8@example.com", "match9@example.com"
    )

    resp = client.post(
        f"/v1/matches/{match_id}/feedback",
        params={"acting_profile_id": a_profile},
        json={"rating": 4, "comment": "Nice conversation"},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 4


def test_submit_outcome_requires_consent(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, match_id = _create_match(
        monkeypatch, "match10@example.com", "match11@example.com"
    )

    denied = client.post(
        f"/v1/matches/{match_id}/outcomes",
        params={"acting_profile_id": a_profile},
        json={"outcome": "engaged", "consent": False},
        headers=_auth_headers(a_tokens),
    )
    assert denied.status_code == 422
    assert denied.json()["code"] == "MATCH_OUTCOME_CONSENT_REQUIRED"

    allowed = client.post(
        f"/v1/matches/{match_id}/outcomes",
        params={"acting_profile_id": a_profile},
        json={"outcome": "engaged", "consent": True},
        headers=_auth_headers(a_tokens),
    )
    assert allowed.status_code == 201
    assert allowed.json()["outcome"] == "engaged"


def test_matches_require_auth(dynamo_table):
    resp = client.get("/v1/matches", params={"acting_profile_id": "x"})
    assert resp.status_code == 401
