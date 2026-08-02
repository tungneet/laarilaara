"""Tests for the main preferences summary and its five preference-set
sub-collections (catalog §5 — "Sections" batch E)."""
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


def test_preferences_get_defaults_empty_then_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    empty = client.get(f"/v1/profiles/{profile_id}/preferences", headers=_auth_headers(tokens))
    assert empty.status_code == 200
    assert empty.json()["age_min"] is None
    assert empty.json()["priorities"] == []

    put = client.put(
        f"/v1/profiles/{profile_id}/preferences",
        json={
            "age_min": 25,
            "age_max": 35,
            "height_min_cm": 160,
            "height_max_cm": 190,
            "priorities": ["education", "family_values"],
            "notes": "Open-minded and family-oriented",
        },
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["age_min"] == 25
    assert put.json()["priorities"] == ["education", "family_values"]


def test_preferences_put_fully_replaces_not_merges(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    client.put(
        f"/v1/profiles/{profile_id}/preferences",
        json={"age_min": 25, "age_max": 35},
        headers=_auth_headers(tokens),
    )
    second = client.put(
        f"/v1/profiles/{profile_id}/preferences",
        json={"age_min": 28},
        headers=_auth_headers(tokens),
    )
    assert second.status_code == 200
    assert second.json()["age_min"] == 28
    assert second.json()["age_max"] is None


def test_preferred_countries_get_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/preferences/countries",
        json={"values": ["IN", "CA"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert set(put.json()["values"]) == {"IN", "CA"}

    get = client.get(
        f"/v1/profiles/{profile_id}/preferences/countries", headers=_auth_headers(tokens)
    )
    assert set(get.json()["values"]) == {"IN", "CA"}


def test_preferred_countries_rejects_unknown_code(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.put(
        f"/v1/profiles/{profile_id}/preferences/countries",
        json={"values": ["ZZ"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "PROFILE_SET_INVALID_VALUE"


def test_preferred_languages_get_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/preferences/languages",
        json={"values": ["pa", "en"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert set(put.json()["values"]) == {"pa", "en"}


def test_preferred_communities_get_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/preferences/communities",
        json={"values": ["jatt-sikh"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["values"] == ["jatt-sikh"]


def test_preferred_religious_practices_get_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref7@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/preferences/religious-practices",
        json={"values": ["amritdhari"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["values"] == ["amritdhari"]


def test_preferred_education_levels_get_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref8@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    put = client.put(
        f"/v1/profiles/{profile_id}/preferences/education-levels",
        json={"values": ["bachelors", "masters"]},
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert set(put.json()["values"]) == {"bachelors", "masters"}


def test_preferences_put_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref9@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.put(
        f"/v1/profiles/{profile_id}/preferences",
        json={"age_min": 30},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_preference_set_put_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pref10@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.put(
        f"/v1/profiles/{profile_id}/preferences/countries",
        json={"values": ["IN"]},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_preferences_endpoints_return_404_for_non_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(
        monkeypatch, "pref11a@example.com", "correct horse battery"
    )
    other_tokens = _register_verify_login(
        monkeypatch, "pref11b@example.com", "correct horse battery"
    )
    profile_id = _create_profile(owner_tokens)

    resp = client.get(
        f"/v1/profiles/{profile_id}/preferences", headers=_auth_headers(other_tokens)
    )
    assert resp.status_code == 404


def test_preferences_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/preferences")
    assert resp.status_code == 401
