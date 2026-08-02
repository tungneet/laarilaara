"""Tests for catalog §12 "Notifications" (7 HTTP operations).

All resources here are account-scoped (like sessions/consents), not
profile-scoped. No SQS-triggered notification worker exists anywhere in
this codebase yet, so nothing in the running API creates notifications —
tests seed them directly via `notifications_repo.create_notification`
(white-box, same pattern as `test_trust_and_safety.py` seeding moderation
actions).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import notification_center as notifications_repo

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


def _account_id(tokens: dict) -> str:
    import jwt

    from app.core.config import get_settings

    payload = jwt.decode(tokens["access_token"], get_settings().jwt_secret, algorithms=["HS256"])
    return payload["sub"]


# ---- Notifications ---------------------------------------------------------


def test_list_notifications_newest_first_and_paginates(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-a@example.com", "correct horse battery")
    account_id = _account_id(tokens)

    for i in range(3):
        notifications_repo.create_notification(account_id, "system", f"Notice {i}", "body", None)

    resp = client.get("/v1/notifications", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    # Newest first.
    assert body["items"][0]["title"] == "Notice 2"

    page1 = client.get("/v1/notifications", params={"limit": 2}, headers=_auth_headers(tokens)).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None
    page2 = client.get(
        "/v1/notifications",
        params={"limit": 2, "cursor": page1["next_cursor"]},
        headers=_auth_headers(tokens),
    ).json()
    assert len(page2["items"]) == 1
    assert page2["next_cursor"] is None


def test_notifications_are_account_scoped(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "notif-b@example.com", "correct horse battery")
    b_tokens = _register_verify_login(monkeypatch, "notif-c@example.com", "correct horse battery")
    a_account = _account_id(a_tokens)

    notifications_repo.create_notification(a_account, "system", "For A only", "body", None)

    b_resp = client.get("/v1/notifications", headers=_auth_headers(b_tokens)).json()
    assert b_resp["items"] == []


def test_mark_notification_read_idempotent_and_not_owned_404(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "notif-d@example.com", "correct horse battery")
    b_tokens = _register_verify_login(monkeypatch, "notif-e@example.com", "correct horse battery")
    a_account = _account_id(a_tokens)

    notification = notifications_repo.create_notification(a_account, "message", "New message", "body", None)

    resp = client.post(
        f"/v1/notifications/{notification['id']}/read", headers=_auth_headers(a_tokens)
    )
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None

    # Idempotent re-mark.
    resp2 = client.post(
        f"/v1/notifications/{notification['id']}/read", headers=_auth_headers(a_tokens)
    )
    assert resp2.status_code == 200

    # A different account cannot mark it (existence-masking 404).
    forbidden = client.post(
        f"/v1/notifications/{notification['id']}/read", headers=_auth_headers(b_tokens)
    )
    assert forbidden.status_code == 404


def test_mark_all_read(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-f@example.com", "correct horse battery")
    account_id = _account_id(tokens)

    for i in range(3):
        notifications_repo.create_notification(account_id, "system", f"N{i}", "body", None)

    resp = client.post("/v1/notifications/read-all", json={}, headers=_auth_headers(tokens))
    assert resp.status_code == 204

    listed = client.get("/v1/notifications", headers=_auth_headers(tokens)).json()
    assert all(item["read_at"] is not None for item in listed["items"])


def test_notifications_require_auth(dynamo_table):
    resp = client.get("/v1/notifications")
    assert resp.status_code == 401


# ---- Notification preferences ----------------------------------------------


def test_notification_preferences_default_and_replace(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-g@example.com", "correct horse battery")

    default_resp = client.get("/v1/notification-preferences", headers=_auth_headers(tokens))
    assert default_resp.status_code == 200
    assert "message" in default_resp.json()["categories"]

    put_resp = client.put(
        "/v1/notification-preferences",
        json={"categories": {"message": ["in_app"], "match": ["in_app", "email"]}},
        headers=_auth_headers(tokens),
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["categories"]["message"] == ["in_app"]

    get_resp = client.get("/v1/notification-preferences", headers=_auth_headers(tokens))
    assert get_resp.json()["categories"]["match"] == ["in_app", "email"]


def test_notification_preferences_invalid_category_is_422(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-h@example.com", "correct horse battery")

    resp = client.put(
        "/v1/notification-preferences",
        json={"categories": {"not-a-real-category": ["in_app"]}},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_notification_preferences_invalid_channel_is_422(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-i@example.com", "correct horse battery")

    resp = client.put(
        "/v1/notification-preferences",
        json={"categories": {"system": ["carrier-pigeon"]}},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


# ---- Push endpoints ---------------------------------------------------------


def test_push_endpoint_register_and_revoke(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-j@example.com", "correct horse battery")

    create_resp = client.post(
        "/v1/push-endpoints",
        json={"platform": "web", "token": "some-provider-token"},
        headers=_auth_headers(tokens),
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["platform"] == "web"
    assert "token" not in body

    delete_resp = client.delete(f"/v1/push-endpoints/{body['id']}", headers=_auth_headers(tokens))
    assert delete_resp.status_code == 204


def test_push_endpoint_revoke_not_owned_is_404(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "notif-k@example.com", "correct horse battery")
    b_tokens = _register_verify_login(monkeypatch, "notif-l@example.com", "correct horse battery")

    created = client.post(
        "/v1/push-endpoints",
        json={"platform": "ios", "token": "abc"},
        headers=_auth_headers(a_tokens),
    ).json()

    resp = client.delete(f"/v1/push-endpoints/{created['id']}", headers=_auth_headers(b_tokens))
    assert resp.status_code == 404


def test_push_endpoint_revoke_unknown_is_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "notif-m@example.com", "correct horse battery")

    resp = client.delete("/v1/push-endpoints/does-not-exist", headers=_auth_headers(tokens))
    assert resp.status_code == 404
