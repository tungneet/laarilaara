"""Tests for raw media assets (catalog §6: uploads/media asset lifecycle)."""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

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


_CONTENT = b"fake image bytes"
_CHECKSUM = hashlib.sha256(_CONTENT).hexdigest()


def test_local_upload_url_is_unsigned_and_url_encoded(monkeypatch):
    settings = SimpleNamespace(
        storage=SimpleNamespace(s3_endpoint_url="http://127.0.0.1:5000/")
    )
    monkeypatch.setattr(s3, "get_settings", lambda: settings)

    url = s3.generate_presigned_put_url(
        "local media", "uploads/profile photo.jpg", "image/jpeg"
    )

    assert url == "http://127.0.0.1:5000/local%20media/uploads/profile%20photo.jpg"
    assert "?" not in url


def _create_upload(tokens: dict) -> dict:
    resp = client.post(
        "/v1/uploads",
        json={
            "purpose": "profile_photo",
            "content_type": "image/jpeg",
            "size_bytes": len(_CONTENT),
            "checksum": _CHECKSUM,
        },
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_upload_returns_presigned_url(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up1@example.com", "correct horse battery")
    body = _create_upload(tokens)
    assert body["status"] == "pending"
    assert body["upload_url"].startswith("http")


def test_create_upload_is_idempotent_by_checksum(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up2@example.com", "correct horse battery")
    first = _create_upload(tokens)
    second = _create_upload(tokens)
    assert first["id"] == second["id"]


def test_complete_upload_marks_ready(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up3@example.com", "correct horse battery")
    asset = _create_upload(tokens)

    # Simulate the client having PUT the bytes to the presigned URL.
    stored = media_assets_repo.get_asset(asset["id"])
    s3.get_s3_client().put_object(
        Bucket=media_bucket, Key=stored["storage_key"], Body=_CONTENT
    )

    resp = client.post(
        f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "ready"


def test_complete_upload_missing_object_returns_404(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up4@example.com", "correct horse battery")
    asset = _create_upload(tokens)

    resp = client.post(
        f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "MEDIA_UPLOAD_OBJECT_MISSING"


def test_complete_upload_size_mismatch_returns_422(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up5@example.com", "correct horse battery")
    asset = _create_upload(tokens)
    stored = media_assets_repo.get_asset(asset["id"])
    s3.get_s3_client().put_object(
        Bucket=media_bucket, Key=stored["storage_key"], Body=b"different length body!!"
    )

    resp = client.post(
        f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "MEDIA_UPLOAD_SIZE_MISMATCH"


def test_complete_upload_is_idempotent_when_already_ready(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up6@example.com", "correct horse battery")
    asset = _create_upload(tokens)
    stored = media_assets_repo.get_asset(asset["id"])
    s3.get_s3_client().put_object(Bucket=media_bucket, Key=stored["storage_key"], Body=_CONTENT)
    client.post(f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens))

    resp = client.post(f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens))
    assert resp.status_code == 202
    assert resp.json()["status"] == "ready"


def test_get_media_returns_download_url_only_when_ready(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up7@example.com", "correct horse battery")
    asset = _create_upload(tokens)

    pending = client.get(f"/v1/media/{asset['id']}", headers=_auth_headers(tokens))
    assert pending.status_code == 200
    assert pending.json()["download_url"] is None

    stored = media_assets_repo.get_asset(asset["id"])
    s3.get_s3_client().put_object(Bucket=media_bucket, Key=stored["storage_key"], Body=_CONTENT)
    client.post(f"/v1/uploads/{asset['id']}/complete", headers=_auth_headers(tokens))

    ready = client.get(f"/v1/media/{asset['id']}", headers=_auth_headers(tokens))
    assert ready.status_code == 200
    assert ready.json()["download_url"].startswith("http")


def test_get_media_masks_other_accounts_asset_as_404(media_bucket, monkeypatch):
    tokens1 = _register_verify_login(monkeypatch, "up8a@example.com", "correct horse battery")
    tokens2 = _register_verify_login(monkeypatch, "up8b@example.com", "correct horse battery")
    asset = _create_upload(tokens1)

    resp = client.get(f"/v1/media/{asset['id']}", headers=_auth_headers(tokens2))
    assert resp.status_code == 404
    assert resp.json()["code"] == "MEDIA_ASSET_NOT_FOUND"


def test_delete_media_is_idempotent(media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "up9@example.com", "correct horse battery")
    asset = _create_upload(tokens)

    first = client.delete(f"/v1/media/{asset['id']}", headers=_auth_headers(tokens))
    assert first.status_code == 204
    second = client.delete(f"/v1/media/{asset['id']}", headers=_auth_headers(tokens))
    assert second.status_code == 204
