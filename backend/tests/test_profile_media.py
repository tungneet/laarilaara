"""Tests for profile media attachments (catalog §6:
`GET/POST /v1/profiles/{profileId}/media`,
`PATCH/DELETE /v1/profiles/{profileId}/media/{profileMediaId}`)."""
from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from app.core import s3
from app.main import app
from app.repositories import media_assets as media_assets_repo

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


def _create_ready_asset(tokens: dict, media_bucket: str, seed: bytes) -> str:
    checksum = hashlib.sha256(seed).hexdigest()
    resp = client.post(
        "/v1/uploads",
        json={
            "purpose": "profile_photo",
            "content_type": "image/jpeg",
            "size_bytes": len(seed),
            "checksum": checksum,
        },
        headers=_auth_headers(tokens),
    )
    asset = resp.json()
    stored = media_assets_repo.get_asset(asset["id"])
    s3.get_s3_client().put_object(Bucket=media_bucket, Key=stored["storage_key"], Body=seed)
    client.post(f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens))
    return asset["id"]


def test_attach_media_then_list(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pm1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    asset_id = _create_ready_asset(tokens, media_bucket, b"photo one")

    attach = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": asset_id, "is_primary": True, "caption": "Main photo"},
        headers=_auth_headers(tokens),
    )
    assert attach.status_code == 201
    assert attach.json()["is_primary"] is True

    listing = client.get(f"/v1/profiles/{profile_id}/media", headers=_auth_headers(tokens))
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_attach_media_rejects_not_ready_asset(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pm2@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    checksum = hashlib.sha256(b"unfinished").hexdigest()
    upload = client.post(
        "/v1/uploads",
        json={
            "purpose": "profile_photo",
            "content_type": "image/jpeg",
            "size_bytes": 10,
            "checksum": checksum,
        },
        headers=_auth_headers(tokens),
    ).json()

    resp = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": upload["id"]},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "PROFILE_MEDIA_ASSET_NOT_READY"


def test_attach_media_is_idempotent(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pm3@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    asset_id = _create_ready_asset(tokens, media_bucket, b"photo three")

    first = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": asset_id},
        headers=_auth_headers(tokens),
    )
    second = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": asset_id},
        headers=_auth_headers(tokens),
    )
    assert first.json()["id"] == second.json()["id"]


def test_patch_media_enforces_primary_exclusivity(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pm4@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    asset1 = _create_ready_asset(tokens, media_bucket, b"photo four a")
    asset2 = _create_ready_asset(tokens, media_bucket, b"photo four b")

    first = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": asset1, "is_primary": True},
        headers=_auth_headers(tokens),
    ).json()
    second = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": asset2},
        headers=_auth_headers(tokens),
    ).json()

    patched = client.patch(
        f"/v1/profiles/{profile_id}/media/{second['id']}",
        json={"is_primary": True},
        headers=_auth_headers(tokens),
    )
    assert patched.status_code == 200
    assert patched.json()["is_primary"] is True

    listing = client.get(f"/v1/profiles/{profile_id}/media", headers=_auth_headers(tokens)).json()
    primary_flags = {item["id"]: item["is_primary"] for item in listing}
    assert primary_flags[first["id"]] is False
    assert primary_flags[second["id"]] is True


def test_delete_media_detaches(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pm5@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    asset_id = _create_ready_asset(tokens, media_bucket, b"photo five")
    attached = client.post(
        f"/v1/profiles/{profile_id}/media",
        json={"asset_id": asset_id},
        headers=_auth_headers(tokens),
    ).json()

    resp = client.delete(
        f"/v1/profiles/{profile_id}/media/{attached['id']}", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 204

    listing = client.get(f"/v1/profiles/{profile_id}/media", headers=_auth_headers(tokens))
    assert listing.json() == []


def test_delete_media_unknown_record_returns_404(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "pm6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.delete(
        f"/v1/profiles/{profile_id}/media/does-not-exist", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_MEDIA_NOT_FOUND"
