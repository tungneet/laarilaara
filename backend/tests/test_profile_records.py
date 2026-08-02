"""Tests for education and employment records (catalog §5 — "Sections"
batch C)."""
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


def test_education_list_add_get_patch_delete_flow(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    empty = client.get(f"/v1/profiles/{profile_id}/education", headers=_auth_headers(tokens))
    assert empty.status_code == 200
    assert empty.json() == []

    created = client.post(
        f"/v1/profiles/{profile_id}/education",
        json={
            "institution": "Punjab University",
            "education_level": "bachelors",
            "field_of_study": "Computer Science",
            "start_year": 2010,
            "end_year": 2014,
        },
        headers=_auth_headers(tokens),
    )
    assert created.status_code == 201
    record_id = created.json()["id"]
    assert created.json()["institution"] == "Punjab University"

    listed = client.get(f"/v1/profiles/{profile_id}/education", headers=_auth_headers(tokens))
    assert len(listed.json()) == 1

    fetched = client.get(
        f"/v1/profiles/{profile_id}/education/{record_id}", headers=_auth_headers(tokens)
    )
    assert fetched.status_code == 200
    assert fetched.json()["field_of_study"] == "Computer Science"

    patched = client.patch(
        f"/v1/profiles/{profile_id}/education/{record_id}",
        json={"end_year": 2015, "is_current": False},
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200
    assert patched.json()["end_year"] == 2015
    assert patched.json()["institution"] == "Punjab University"

    deleted = client.delete(
        f"/v1/profiles/{profile_id}/education/{record_id}", headers=_auth_headers(tokens)
    )
    assert deleted.status_code == 204

    after_delete = client.get(
        f"/v1/profiles/{profile_id}/education/{record_id}", headers=_auth_headers(tokens)
    )
    assert after_delete.status_code == 404
    assert after_delete.json()["code"] == "PROFILE_EDUCATION_RECORD_NOT_FOUND"


def test_education_add_rejects_invalid_level(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        f"/v1/profiles/{profile_id}/education",
        json={"institution": "Some College", "education_level": "not-a-real-level"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "PROFILE_RECORD_INVALID_VALUE"


def test_education_patch_unknown_record_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/education/nonexistent",
        json={"end_year": 2020},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_EDUCATION_RECORD_NOT_FOUND"


def test_education_delete_unknown_record_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.delete(
        f"/v1/profiles/{profile_id}/education/nonexistent", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404


def test_employment_list_add_get_patch_delete_flow(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    created = client.post(
        f"/v1/profiles/{profile_id}/employment",
        json={
            "employer": "Acme Corp",
            "occupation_category": "engineering-it",
            "job_title": "Software Engineer",
            "is_current": True,
        },
        headers=_auth_headers(tokens),
    )
    assert created.status_code == 201
    record_id = created.json()["id"]

    listed = client.get(f"/v1/profiles/{profile_id}/employment", headers=_auth_headers(tokens))
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/v1/profiles/{profile_id}/employment/{record_id}",
        json={"job_title": "Senior Software Engineer"},
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200
    assert patched.json()["job_title"] == "Senior Software Engineer"
    assert patched.json()["employer"] == "Acme Corp"

    deleted = client.delete(
        f"/v1/profiles/{profile_id}/employment/{record_id}", headers=_auth_headers(tokens)
    )
    assert deleted.status_code == 204


def test_employment_add_rejects_invalid_category(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        f"/v1/profiles/{profile_id}/employment",
        json={"employer": "Acme Corp", "occupation_category": "not-a-real-category"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_records_bump_profile_version_on_add(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "rec7@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.post(
        f"/v1/profiles/{profile_id}/education",
        json={"institution": "Some College", "education_level": "bachelors"},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_record_endpoints_return_404_for_non_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "rec8a@example.com", "correct horse battery")
    other_tokens = _register_verify_login(monkeypatch, "rec8b@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    resp = client.get(
        f"/v1/profiles/{profile_id}/education", headers=_auth_headers(other_tokens)
    )
    assert resp.status_code == 404


def test_record_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/education")
    assert resp.status_code == 401
