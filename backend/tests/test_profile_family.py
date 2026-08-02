"""Tests for the family section (catalog §5 — "Sections" batch D)."""
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


def test_family_get_defaults_empty_then_put(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    empty = client.get(f"/v1/profiles/{profile_id}/family", headers=_auth_headers(tokens))
    assert empty.status_code == 200
    assert empty.json() == {
        "family_type": None,
        "father_living": None,
        "mother_living": None,
        "siblings_count": None,
        "family_values": None,
        "updated_at": None,
    }

    put = client.put(
        f"/v1/profiles/{profile_id}/family",
        json={
            "family_type": "nuclear",
            "father_living": True,
            "mother_living": True,
            "siblings_count": 2,
            "family_values": "Close-knit and supportive",
        },
        headers=_auth_headers(tokens),
    )
    assert put.status_code == 200
    assert put.json()["family_type"] == "nuclear"
    assert put.json()["siblings_count"] == 2


def test_family_put_fully_replaces_not_merges(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    client.put(
        f"/v1/profiles/{profile_id}/family",
        json={"family_type": "joint", "siblings_count": 3},
        headers=_auth_headers(tokens),
    )
    second = client.put(
        f"/v1/profiles/{profile_id}/family",
        json={"family_type": "nuclear"},
        headers=_auth_headers(tokens),
    )
    assert second.status_code == 200
    assert second.json()["family_type"] == "nuclear"
    assert second.json()["siblings_count"] is None


def test_family_members_list_add_patch_delete_flow(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    empty = client.get(
        f"/v1/profiles/{profile_id}/family/members", headers=_auth_headers(tokens)
    )
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        f"/v1/profiles/{profile_id}/family/members",
        json={"relation": "brother", "name": "Aman", "age": 30, "occupation": "Engineer"},
        headers=_auth_headers(tokens),
    )
    assert created.status_code == 201
    member_id = created.json()["id"]
    assert created.json()["name"] == "Aman"

    listed = client.get(
        f"/v1/profiles/{profile_id}/family/members", headers=_auth_headers(tokens)
    )
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/v1/profiles/{profile_id}/family/members/{member_id}",
        json={"age": 31, "is_married": True},
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200
    assert patched.json()["age"] == 31
    assert patched.json()["name"] == "Aman"

    deleted = client.delete(
        f"/v1/profiles/{profile_id}/family/members/{member_id}",
        headers=_auth_headers(tokens),
    )
    assert deleted.status_code == 204

    after_delete = client.get(
        f"/v1/profiles/{profile_id}/family/members", headers=_auth_headers(tokens)
    )
    assert after_delete.json() == []


def test_family_member_patch_unknown_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/family/members/does-not-exist",
        json={"age": 40},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404


def test_family_member_delete_unknown_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.delete(
        f"/v1/profiles/{profile_id}/family/members/does-not-exist",
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404


def test_family_put_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.put(
        f"/v1/profiles/{profile_id}/family",
        json={"family_type": "extended"},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_family_member_add_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "fam7@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.post(
        f"/v1/profiles/{profile_id}/family/members",
        json={"relation": "sister", "name": "Simran"},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_family_endpoints_return_404_for_non_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "fam8a@example.com", "correct horse battery")
    other_tokens = _register_verify_login(monkeypatch, "fam8b@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    resp = client.get(f"/v1/profiles/{profile_id}/family", headers=_auth_headers(other_tokens))
    assert resp.status_code == 404


def test_family_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/family")
    assert resp.status_code == 401
