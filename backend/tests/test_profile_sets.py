"""Tests for the replace-set profile sections (catalog §5 — "Sections" batch
B: communities, religious-practices, languages, interests)."""
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


def test_communities_get_defaults_empty_then_put_replaces(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    initial = client.get(
        f"/v1/profiles/{profile_id}/communities", headers=_auth_headers(tokens)
    )
    assert initial.status_code == 200
    assert initial.json()["values"] == []

    put_resp = client.put(
        f"/v1/profiles/{profile_id}/communities",
        json={"values": ["jatt-sikh", "arora"]},
        headers=_auth_headers(tokens),
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["values"] == ["jatt-sikh", "arora"]

    reread = client.get(f"/v1/profiles/{profile_id}/communities", headers=_auth_headers(tokens))
    assert reread.json()["values"] == ["jatt-sikh", "arora"]


def test_communities_put_fully_replaces_not_merges(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    client.put(
        f"/v1/profiles/{profile_id}/communities",
        json={"values": ["jatt-sikh", "arora"]},
        headers=_auth_headers(tokens),
    )
    second = client.put(
        f"/v1/profiles/{profile_id}/communities",
        json={"values": ["khatri-sikh"]},
        headers=_auth_headers(tokens),
    )
    assert second.json()["values"] == ["khatri-sikh"]


def test_communities_put_rejects_unknown_value(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/communities",
        json={"values": ["not-a-real-community"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "PROFILE_SET_INVALID_VALUE"


def test_religious_practices_get_and_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/religious-practices",
        json={"values": ["amritdhari"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["values"] == ["amritdhari"]


def test_languages_get_and_put_uses_language_codes(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/languages",
        json={"values": ["pa", "en"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["values"] == ["pa", "en"]


def test_languages_put_rejects_unknown_code(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/languages",
        json={"values": ["xx"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_interests_get_and_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set7@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/interests",
        json={"values": ["cooking", "travel"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["values"] == ["cooking", "travel"]


def test_set_put_dedupes_values(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set8@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/interests",
        json={"values": ["cooking", "cooking", "travel"]},
        headers=_auth_headers(tokens),
    )
    assert resp.json()["values"] == ["cooking", "travel"]


def test_set_put_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "set9@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.put(
        f"/v1/profiles/{profile_id}/interests",
        json={"values": ["cooking"]},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_set_endpoints_return_404_for_non_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "set10a@example.com", "correct horse battery")
    other_tokens = _register_verify_login(monkeypatch, "set10b@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    resp = client.get(
        f"/v1/profiles/{profile_id}/interests", headers=_auth_headers(other_tokens)
    )
    assert resp.status_code == 404


def test_set_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/interests")
    assert resp.status_code == 401
