"""Tests for interests (catalog §8: `GET/POST /v1/interests`,
`POST /v1/interests/{interestId}/accept|decline|withdraw`)."""
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


def test_send_interest_then_list_outgoing_and_incoming(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "int1@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "int2@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    send = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile, "message": "Hi there"},
        headers=_auth_headers(a_tokens),
    )
    assert send.status_code == 201
    assert send.json()["status"] == "pending"

    outgoing = client.get(
        "/v1/interests",
        params={"acting_profile_id": a_profile, "direction": "outgoing"},
        headers=_auth_headers(a_tokens),
    )
    assert outgoing.status_code == 200
    assert len(outgoing.json()["items"]) == 1

    incoming = client.get(
        "/v1/interests",
        params={"acting_profile_id": b_profile, "direction": "incoming"},
        headers=_auth_headers(b_tokens),
    )
    assert incoming.status_code == 200
    assert len(incoming.json()["items"]) == 1


def test_send_interest_is_idempotent_while_pending(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "int3@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "int4@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    first = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    )
    second = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    )
    assert first.json()["id"] == second.json()["id"]


def test_send_interest_to_self_is_rejected(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "int5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        "/v1/interests",
        params={"acting_profile_id": profile_id},
        json={"target_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "INTEREST_SELF_TARGET"


def test_accept_interest_creates_match(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "int6@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "int7@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    sent = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    ).json()

    accept = client.post(
        f"/v1/interests/{sent['id']}/accept",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    )
    assert accept.status_code == 200
    body = accept.json()
    assert body["status"] == "accepted"
    assert body["match_id"] is not None

    match_resp = client.get(
        f"/v1/matches/{body['match_id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert match_resp.status_code == 200
    assert match_resp.json()["status"] == "active"


def test_accept_interest_by_non_recipient_is_404(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "int8@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "int9@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    sent = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    ).json()

    resp = client.post(
        f"/v1/interests/{sent['id']}/accept",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "INTEREST_NOT_FOUND"


def test_decline_interest_is_idempotent(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "int10@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "int11@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    sent = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    ).json()

    first = client.post(
        f"/v1/interests/{sent['id']}/decline",
        params={"acting_profile_id": b_profile},
        json={"reason": "Not a match"},
        headers=_auth_headers(b_tokens),
    )
    second = client.post(
        f"/v1/interests/{sent['id']}/decline",
        params={"acting_profile_id": b_profile},
        json={},
        headers=_auth_headers(b_tokens),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "declined"
    assert second.json()["status"] == "declined"


def test_withdraw_interest_then_accept_conflicts(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "int12@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "int13@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    sent = client.post(
        "/v1/interests",
        params={"acting_profile_id": a_profile},
        json={"target_profile_id": b_profile},
        headers=_auth_headers(a_tokens),
    ).json()

    withdraw = client.post(
        f"/v1/interests/{sent['id']}/withdraw",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert withdraw.status_code == 200
    assert withdraw.json()["status"] == "withdrawn"

    accept = client.post(
        f"/v1/interests/{sent['id']}/accept",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    )
    assert accept.status_code == 409
    assert accept.json()["code"] == "INTEREST_STATE_CONFLICT"


def test_interests_require_auth(dynamo_table):
    resp = client.get(
        "/v1/interests", params={"acting_profile_id": "x", "direction": "outgoing"}
    )
    assert resp.status_code == 401
