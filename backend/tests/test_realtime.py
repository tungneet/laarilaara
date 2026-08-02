"""Tests for the realtime WebSocket half (catalog §9):
`POST /v1/realtime-tokens`, `$connect`/`$default`/`$disconnect` (a local
`@router.websocket` equivalent), typing dispatch, and server push on
message send/edit/delete/read.
"""
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


def _create_conversation(monkeypatch, email_a: str, email_b: str) -> tuple[dict, str, dict, str, str]:
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
    match_resp = client.get(
        f"/v1/matches/{accepted['match_id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    ).json()
    return a_tokens, a_profile, b_tokens, b_profile, match_resp["conversation_id"]


def test_issue_realtime_token(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rt1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        "/v1/realtime-tokens",
        json={"profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token"]
    assert body["expires_in"] > 0


def test_realtime_token_rejects_non_owned_profile(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rt2@example.com", "correct horse battery")
    _create_profile(tokens)
    other_tokens = _register_verify_login(monkeypatch, "rt3@example.com", "correct horse battery")
    other_profile = _create_profile(other_tokens)

    resp = client.post(
        "/v1/realtime-tokens",
        json={"profile_id": other_profile},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404


def test_websocket_connect_rejects_invalid_token(dynamo_table):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/v1/realtime?token=garbage"):
            pass


def test_websocket_connect_and_receive_message_created_push(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "rt4@example.com", "rt5@example.com"
    )

    b_token_resp = client.post(
        "/v1/realtime-tokens",
        json={"profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    ).json()

    with client.websocket_connect(f"/v1/realtime?token={b_token_resp['token']}") as ws:
        send_resp = client.post(
            f"/v1/conversations/{conversation_id}/messages",
            params={"acting_profile_id": a_profile},
            json={"client_message_id": "msg-1", "body": "hello"},
            headers=_auth_headers(a_tokens),
        )
        assert send_resp.status_code == 201

        event = ws.receive_json()
        assert event["type"] == "message.created"
        assert event["payload"]["body"] == "hello"


def test_websocket_typing_dispatch(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "rt6@example.com", "rt7@example.com"
    )

    a_token_resp = client.post(
        "/v1/realtime-tokens",
        json={"profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    ).json()
    b_token_resp = client.post(
        "/v1/realtime-tokens",
        json={"profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    ).json()

    with client.websocket_connect(f"/v1/realtime?token={a_token_resp['token']}") as ws_a:
        with client.websocket_connect(f"/v1/realtime?token={b_token_resp['token']}") as ws_b:
            ws_a.send_json({"action": "typing.start", "conversationId": conversation_id})
            event = ws_b.receive_json()
            assert event["type"] == "typing.changed"
            assert event["payload"]["typing"] is True
            assert event["payload"]["profileId"] == a_profile
