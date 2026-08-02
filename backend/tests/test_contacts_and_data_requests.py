"""Tests for /v1/me/contacts and /v1/me/data-requests (catalog §4)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register_and_capture_challenge(monkeypatch, email: str, password: str) -> tuple[str, str]:
    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    client.post("/v1/auth/register", json={"email": email, "password": password})
    return captured["challenge_id"], captured["code"]


def _register_verify_login(monkeypatch, email: str, password: str) -> dict:
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)
    client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


def _auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_add_contact_masks_value_and_is_unverified(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts1@example.com", "correct horse battery")

    monkeypatch.setattr("app.services.contacts.send_verification_code", lambda *a, **k: None)
    resp = client.post(
        "/v1/me/contacts",
        json={"type": "email", "value": "alt@example.com"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["verified"] is False
    assert body["masked_value"] == "a***@example.com"


def test_verify_contact_flow(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts2@example.com", "correct horse battery")

    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code

    monkeypatch.setattr("app.services.contacts.send_verification_code", fake_send)
    add_resp = client.post(
        "/v1/me/contacts",
        json={"type": "phone", "value": "+15551234567"},
        headers=_auth_headers(tokens),
    )
    contact_id = add_resp.json()["id"]

    verify_resp = client.post(
        f"/v1/me/contacts/{contact_id}/verify",
        json={"code": captured["code"]},
        headers=_auth_headers(tokens),
    )
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True


def test_verify_contact_rejects_wrong_code(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts3@example.com", "correct horse battery")
    monkeypatch.setattr("app.services.contacts.send_verification_code", lambda *a, **k: None)

    add_resp = client.post(
        "/v1/me/contacts",
        json={"type": "email", "value": "alt3@example.com"},
        headers=_auth_headers(tokens),
    )
    contact_id = add_resp.json()["id"]

    resp = client.post(
        f"/v1/me/contacts/{contact_id}/verify",
        json={"code": "000000"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "CONTACT_CHALLENGE_INVALID"


def test_add_contact_is_idempotent_for_unverified_duplicates(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts4@example.com", "correct horse battery")
    monkeypatch.setattr("app.services.contacts.send_verification_code", lambda *a, **k: None)

    first = client.post(
        "/v1/me/contacts",
        json={"type": "email", "value": "dup@example.com"},
        headers=_auth_headers(tokens),
    )
    second = client.post(
        "/v1/me/contacts",
        json={"type": "email", "value": "dup@example.com"},
        headers=_auth_headers(tokens),
    )
    assert first.json()["id"] == second.json()["id"]

    listed = client.get("/v1/me/contacts", headers=_auth_headers(tokens))
    assert len(listed.json()) == 1


def test_cannot_remove_last_verified_contact(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts5@example.com", "correct horse battery")

    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code

    monkeypatch.setattr("app.services.contacts.send_verification_code", fake_send)
    add_resp = client.post(
        "/v1/me/contacts",
        json={"type": "email", "value": "onlyverified@example.com"},
        headers=_auth_headers(tokens),
    )
    contact_id = add_resp.json()["id"]
    client.post(
        f"/v1/me/contacts/{contact_id}/verify",
        json={"code": captured["code"]},
        headers=_auth_headers(tokens),
    )

    resp = client.delete(f"/v1/me/contacts/{contact_id}", headers=_auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["code"] == "CANNOT_REMOVE_LAST_VERIFIED_CONTACT"


def test_can_remove_unverified_contact(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts6@example.com", "correct horse battery")
    monkeypatch.setattr("app.services.contacts.send_verification_code", lambda *a, **k: None)

    add_resp = client.post(
        "/v1/me/contacts",
        json={"type": "email", "value": "removable@example.com"},
        headers=_auth_headers(tokens),
    )
    contact_id = add_resp.json()["id"]

    resp = client.delete(f"/v1/me/contacts/{contact_id}", headers=_auth_headers(tokens))
    assert resp.status_code == 204


def test_remove_unknown_contact_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "contacts7@example.com", "correct horse battery")

    resp = client.delete("/v1/me/contacts/does-not-exist", headers=_auth_headers(tokens))
    assert resp.status_code == 404
    assert resp.json()["code"] == "CONTACT_NOT_FOUND"


def test_contacts_require_bearer_token(dynamo_table):
    resp = client.get("/v1/me/contacts")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_create_and_read_data_request(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "datareq1@example.com", "correct horse battery")

    create_resp = client.post(
        "/v1/me/data-requests",
        json={"type": "export", "details": "please send my data"},
        headers=_auth_headers(tokens),
    )
    assert create_resp.status_code == 202
    body = create_resp.json()
    assert body["status"] == "queued"
    assert body["type"] == "export"

    get_resp = client.get(
        f"/v1/me/data-requests/{body['id']}", headers=_auth_headers(tokens)
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


def test_data_request_not_found(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "datareq2@example.com", "correct horse battery")

    resp = client.get("/v1/me/data-requests/does-not-exist", headers=_auth_headers(tokens))
    assert resp.status_code == 404
    assert resp.json()["code"] == "DATA_REQUEST_NOT_FOUND"


def test_data_requests_require_bearer_token(dynamo_table):
    resp = client.post("/v1/me/data-requests", json={"type": "export"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"
