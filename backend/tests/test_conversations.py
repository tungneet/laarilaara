"""Tests for conversations and messages (catalog §9: `GET /v1/conversations`,
`GET /v1/conversations/{id}`, `GET/POST /v1/conversations/{id}/messages`,
`PATCH/DELETE /v1/conversations/{id}/messages/{messageId}`,
`POST /v1/conversations/{id}/read`, `POST /v1/conversations/{id}/mute`).

A conversation only exists once two profiles have gone through the
send-interest -> accept-interest flow (conversations are 1:1 with matches,
created automatically on accept — see `app.services.interests`).
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


def test_accepting_interest_creates_conversation_visible_to_both(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv1@example.com", "conv2@example.com"
    )
    assert conversation_id is not None

    a_list = client.get(
        "/v1/conversations", params={"acting_profile_id": a_profile}, headers=_auth_headers(a_tokens)
    )
    b_list = client.get(
        "/v1/conversations", params={"acting_profile_id": b_profile}, headers=_auth_headers(b_tokens)
    )
    assert a_list.status_code == 200
    assert b_list.status_code == 200
    assert any(item["id"] == conversation_id for item in a_list.json()["items"])
    assert any(item["id"] == conversation_id for item in b_list.json()["items"])


def test_get_conversation_for_non_participant_is_404(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv3@example.com", "conv4@example.com"
    )
    c_tokens = _register_verify_login(monkeypatch, "conv5@example.com", "correct horse battery")
    c_profile = _create_profile(c_tokens)

    resp = client.get(
        f"/v1/conversations/{conversation_id}",
        params={"acting_profile_id": c_profile},
        headers=_auth_headers(c_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "CONVERSATION_NOT_FOUND"


def test_send_message_then_list_and_unread_count(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv6@example.com", "conv7@example.com"
    )

    send = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "cmid-1", "body": "Hello there"},
        headers=_auth_headers(a_tokens),
    )
    assert send.status_code == 201
    assert send.json()["status"] == "sent"

    messages = client.get(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    )
    assert messages.status_code == 200
    assert len(messages.json()["items"]) == 1

    b_conversation = client.get(
        f"/v1/conversations/{conversation_id}",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    ).json()
    assert b_conversation["unread_count"] == 1
    assert b_conversation["last_message_preview"] == "Hello there"


def test_send_message_blocked_by_moderation(dynamo_table, monkeypatch):
    a_tokens, a_profile, _b_tokens, _b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv-mod1@example.com", "conv-mod2@example.com"
    )

    resp = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "mod-1", "body": "I will kill you"},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "MESSAGE_CONTENT_BLOCKED"

    # The blocked message was never created.
    messages = client.get(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert messages.json()["items"] == []


def test_send_message_is_idempotent_by_client_message_id(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv8@example.com", "conv9@example.com"
    )

    first = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "dup-1", "body": "One"},
        headers=_auth_headers(a_tokens),
    )
    second = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "dup-1", "body": "One"},
        headers=_auth_headers(a_tokens),
    )
    assert first.json()["id"] == second.json()["id"]


def test_send_message_requires_body_or_attachment(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv10@example.com", "conv11@example.com"
    )

    resp = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "empty-1"},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "MESSAGE_EMPTY"


def test_edit_message_by_sender(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv12@example.com", "conv13@example.com"
    )

    sent = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "edit-1", "body": "Original"},
        headers=_auth_headers(a_tokens),
    ).json()

    edited = client.patch(
        f"/v1/conversations/{conversation_id}/messages/{sent['id']}",
        params={"acting_profile_id": a_profile},
        json={"body": "Edited"},
        headers=_auth_headers(a_tokens),
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "Edited"
    assert edited.json()["status"] == "edited"
    assert edited.json()["revision"] == 2


def test_edit_message_by_non_sender_is_404(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv14@example.com", "conv15@example.com"
    )

    sent = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "edit-2", "body": "Original"},
        headers=_auth_headers(a_tokens),
    ).json()

    resp = client.patch(
        f"/v1/conversations/{conversation_id}/messages/{sent['id']}",
        params={"acting_profile_id": b_profile},
        json={"body": "Hijacked"},
        headers=_auth_headers(b_tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "MESSAGE_NOT_FOUND"


def test_delete_message_is_soft_and_idempotent(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv16@example.com", "conv17@example.com"
    )

    sent = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "del-1", "body": "To delete"},
        headers=_auth_headers(a_tokens),
    ).json()

    first = client.delete(
        f"/v1/conversations/{conversation_id}/messages/{sent['id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    second = client.delete(
        f"/v1/conversations/{conversation_id}/messages/{sent['id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "deleted"
    assert first.json()["body"] is None


def test_mark_read_advances_marker_and_clears_unread(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv18@example.com", "conv19@example.com"
    )

    sent = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        params={"acting_profile_id": a_profile},
        json={"client_message_id": "read-1", "body": "Read me"},
        headers=_auth_headers(a_tokens),
    ).json()

    read = client.post(
        f"/v1/conversations/{conversation_id}/read",
        params={"acting_profile_id": b_profile},
        json={"message_id": sent["id"]},
        headers=_auth_headers(b_tokens),
    )
    assert read.status_code == 200
    assert read.json()["unread_count"] == 0


def test_mute_conversation(dynamo_table, monkeypatch):
    a_tokens, a_profile, b_tokens, b_profile, conversation_id = _create_conversation(
        monkeypatch, "conv20@example.com", "conv21@example.com"
    )

    muted = client.post(
        f"/v1/conversations/{conversation_id}/mute",
        params={"acting_profile_id": a_profile},
        json={"muted": True},
        headers=_auth_headers(a_tokens),
    )
    assert muted.status_code == 200
    assert muted.json()["muted"] is True

    # Muting is per-profile: the other participant is unaffected.
    b_view = client.get(
        f"/v1/conversations/{conversation_id}",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    )
    assert b_view.json()["muted"] is False


def test_conversations_require_auth(dynamo_table):
    resp = client.get("/v1/conversations", params={"acting_profile_id": "x"})
    assert resp.status_code == 401
