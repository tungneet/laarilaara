"""Tests for the single-resource profile sections (catalog §5 — "Sections"
batch: personal-details, narratives, lifestyle, visibility)."""
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


def test_personal_details_get_defaults_empty_then_patch_updates(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    initial = client.get(
        f"/v1/profiles/{profile_id}/personal-details", headers=_auth_headers(tokens)
    )
    assert initial.status_code == 200
    assert initial.json()["gender"] is None

    patched = client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={
            "date_of_birth": "1995-06-15",
            "gender": "female",
            "height_cm": 165,
            "marital_status": "never_married",
            "mother_tongue": "Punjabi",
        },
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["gender"] == "female"
    assert body["height_cm"] == 165
    assert body["mother_tongue"] == "Punjabi"
    assert body["updated_at"] is not None

    reread = client.get(
        f"/v1/profiles/{profile_id}/personal-details", headers=_auth_headers(tokens)
    )
    assert reread.json()["marital_status"] == "never_married"


def test_personal_details_patch_is_partial(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"height_cm": 170},
        headers=_auth_headers(tokens),
    )
    second = client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"mother_tongue": "Hindi"},
        headers=_auth_headers(tokens),
    )
    assert second.status_code == 200
    assert second.json()["height_cm"] == 170
    assert second.json()["mother_tongue"] == "Hindi"


def test_personal_details_patch_rejects_invalid_enum(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"gender": "not-a-gender"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_personal_details_patch_rejects_invalid_height(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/personal-details",
        json={"height_cm": 5},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_narratives_get_and_patch(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/narratives",
        json={"headline": "Looking for a life partner", "bio": "I enjoy hiking."},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["headline"] == "Looking for a life partner"

    reread = client.get(f"/v1/profiles/{profile_id}/narratives", headers=_auth_headers(tokens))
    assert reread.json()["bio"] == "I enjoy hiking."


def test_narratives_patch_blocked_by_moderation(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec5b@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/narratives",
        json={"bio": "I want to kill you if you don't reply."},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "NARRATIVE_CONTENT_BLOCKED"

    # The blocked field was never saved.
    reread = client.get(f"/v1/profiles/{profile_id}/narratives", headers=_auth_headers(tokens))
    assert reread.json()["bio"] is None


def test_lifestyle_get_and_patch(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/lifestyle",
        json={"diet": "vegetarian", "smoking": "no", "alcohol": "occasionally"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["diet"] == "vegetarian"
    assert resp.json()["alcohol"] == "occasionally"


def test_lifestyle_patch_rejects_invalid_habit_value(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec7@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/lifestyle",
        json={"smoking": "sometimes"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422


def test_visibility_get_and_patch(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec8@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.patch(
        f"/v1/profiles/{profile_id}/visibility",
        json={
            "discoverable": True,
            "photo_visibility": "connections_only",
            "name_visibility": "public",
        },
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    assert resp.json()["discoverable"] is True
    assert resp.json()["photo_visibility"] == "connections_only"


def test_section_patch_bumps_profile_version(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec9@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    before = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    client.patch(
        f"/v1/profiles/{profile_id}/narratives",
        json={"headline": "Bumping version"},
        headers=_auth_headers(tokens),
    )
    after = client.get(f"/v1/profiles/{profile_id}", headers=_auth_headers(tokens)).json()
    assert after["version"] == before["version"] + 1


def test_section_endpoints_return_404_for_unknown_profile(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "sec10@example.com", "correct horse battery")

    resp = client.get(
        "/v1/profiles/nonexistent/personal-details", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_NOT_FOUND"


def test_section_endpoints_return_404_for_non_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "sec11a@example.com", "correct horse battery")
    other_tokens = _register_verify_login(monkeypatch, "sec11b@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    resp = client.get(
        f"/v1/profiles/{profile_id}/lifestyle", headers=_auth_headers(other_tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_NOT_FOUND"


def test_section_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/visibility")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"
