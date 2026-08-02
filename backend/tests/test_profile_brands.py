"""Tests for brands and experiences (catalog §5 — "Sections" batch F)."""
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


def test_brands_get_defaults_empty_then_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "brand1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    empty = client.get(f"/v1/profiles/{profile_id}/brands", headers=_auth_headers(tokens))
    assert empty.status_code == 200
    assert empty.json()["values"] == []

    put = client.put(
        f"/v1/profiles/{profile_id}/brands",
        json={"values": ["punjabi-matrimony", "sikh-connect"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert set(put.json()["values"]) == {"punjabi-matrimony", "sikh-connect"}


def test_brands_put_rejects_empty_value(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "brand2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/brands",
        json={"values": [""]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "PROFILE_SET_INVALID_VALUE"


def test_experiences_get_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "brand3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/experiences",
        json={"values": ["speed-dating-event"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["values"] == ["speed-dating-event"]

    get = client.get(f"/v1/profiles/{profile_id}/experiences", headers=_auth_headers(tokens))
    assert get.json()["values"] == ["speed-dating-event"]


def test_experiences_put_dedupes_values(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "brand4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/experiences",
        json={"values": ["a", "b", "a"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["values"] == ["a", "b"]


def test_brands_put_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "brand5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.put(
        f"/v1/profiles/{profile_id}/brands",
        json={"values": ["punjabi-matrimony"]},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_brands_endpoints_return_404_for_non_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(
        monkeypatch, "brand6a@example.com", "correct horse battery"
    )
    other_tokens = _register_verify_login(
        monkeypatch, "brand6b@example.com", "correct horse battery"
    )
    profile_id = _create_profile(owner_tokens)

    resp = client.get(f"/v1/profiles/{profile_id}/brands", headers=_auth_headers(other_tokens))
    assert resp.status_code == 404


def test_brands_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/brands")
    assert resp.status_code == 401
