"""Tests for catalog §11 "Blocks, reports, trust, and verification" (13 HTTP
operations).

Verification requests/claims/trust-summary stay "unverified"/"draft" forever
in this codebase (no admin verification-decision endpoint exists yet) — see
`app/services/verification.py` module docstring KNOWN GAP. Moderation
actions have no creation endpoint either (§15 admin surface unbuilt), so
appeal tests seed an action directly via the repository (white-box, same
pattern as `test_media.py` simulating a presigned upload).
"""
from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import moderation_actions as moderation_actions_repo

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


_CONTENT = b"fake evidence bytes"
_CHECKSUM = hashlib.sha256(_CONTENT).hexdigest()


def _create_upload(tokens: dict) -> dict:
    resp = client.post(
        "/v1/uploads",
        json={
            "purpose": "verification_evidence",
            "content_type": "image/jpeg",
            "size_bytes": len(_CONTENT),
            "checksum": _CHECKSUM,
        },
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    return resp.json()


# ---- Blocks --------------------------------------------------------------


def test_block_list_unblock_flow(dynamo_table, media_bucket, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "block-a@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "block-b@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    put_resp = client.put(
        f"/v1/blocks/{b_profile}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["target_profile_id"] == b_profile

    # Idempotent re-block.
    again = client.put(
        f"/v1/blocks/{b_profile}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert again.status_code == 200

    list_resp = client.get(
        "/v1/blocks", params={"acting_profile_id": a_profile}, headers=_auth_headers(a_tokens)
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    unblock_resp = client.delete(
        f"/v1/blocks/{b_profile}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert unblock_resp.status_code == 204

    # Idempotent unblock of an already-unblocked target.
    again_delete = client.delete(
        f"/v1/blocks/{b_profile}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert again_delete.status_code == 204


def test_blocks_require_auth(dynamo_table):
    resp = client.get("/v1/blocks", params={"acting_profile_id": "someid"})
    assert resp.status_code == 401


# ---- Reports --------------------------------------------------------------


def test_report_create_and_get(dynamo_table, media_bucket, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "report-a@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "report-b@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    create_resp = client.post(
        "/v1/reports",
        params={"acting_profile_id": a_profile},
        json={
            "subject_type": "profile",
            "subject_id": b_profile,
            "reason": "spam",
            "details": "Sends unsolicited links.",
            "evidence_asset_ids": [],
        },
        headers=_auth_headers(a_tokens),
    )
    assert create_resp.status_code == 202
    report = create_resp.json()
    assert report["status"] == "queued"

    get_resp = client.get(
        f"/v1/reports/{report['id']}",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == report["id"]

    # Non-reporter (the reported profile) gets an existence-masking 404.
    forbidden_get = client.get(
        f"/v1/reports/{report['id']}",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    )
    assert forbidden_get.status_code == 404


def test_report_with_unknown_evidence_asset_is_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "report-c@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.post(
        "/v1/reports",
        params={"acting_profile_id": profile_id},
        json={
            "subject_type": "message",
            "subject_id": "msg-123",
            "reason": "abuse",
            "evidence_asset_ids": ["does-not-exist"],
        },
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "MEDIA_ASSET_NOT_FOUND"


# ---- Trust-summary and verification ---------------------------------------


def test_trust_summary_defaults_unverified(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "trust-a@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "trust-b@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    resp = client.get(
        f"/v1/profiles/{b_profile}/trust-summary",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["trust_label"] == "unverified"
    assert body["verified_checks"] == []


def test_verification_options_lists_checks(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "verify-a@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.get(
        f"/v1/profiles/{profile_id}/verification-options",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert "government_id" in ids


def test_verification_request_create_is_idempotent(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "verify-b@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    first = client.post(
        f"/v1/profiles/{profile_id}/verification-requests",
        json={"check_type": "government_id"},
        headers=_auth_headers(tokens),
    )
    assert first.status_code == 202
    assert first.json()["status"] == "draft"

    second = client.post(
        f"/v1/profiles/{profile_id}/verification-requests",
        json={"check_type": "government_id"},
        headers=_auth_headers(tokens),
    )
    assert second.status_code == 202
    assert second.json()["id"] == first.json()["id"]


def test_verification_submit_requires_evidence_then_locks(dynamo_table, media_bucket, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "verify-c@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    created = client.post(
        f"/v1/profiles/{profile_id}/verification-requests",
        json={"check_type": "government_id"},
        headers=_auth_headers(tokens),
    ).json()
    request_id = created["id"]

    submit_no_evidence = client.post(
        f"/v1/verification-requests/{request_id}/submit",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert submit_no_evidence.status_code == 422

    asset = _create_upload(tokens)
    evidence_resp = client.post(
        f"/v1/verification-requests/{request_id}/evidence",
        params={"acting_profile_id": profile_id},
        json={"asset_id": asset["id"]},
        headers=_auth_headers(tokens),
    )
    assert evidence_resp.status_code == 200
    assert asset["id"] in evidence_resp.json()["evidence_asset_ids"]

    submit_resp = client.post(
        f"/v1/verification-requests/{request_id}/submit",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert submit_resp.status_code == 202
    assert submit_resp.json()["status"] == "submitted"

    # Idempotent re-submit.
    resubmit = client.post(
        f"/v1/verification-requests/{request_id}/submit",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(tokens),
    )
    assert resubmit.status_code == 202
    assert resubmit.json()["status"] == "submitted"

    # No more evidence can be added once submitted.
    extra_evidence = client.post(
        f"/v1/verification-requests/{request_id}/evidence",
        params={"acting_profile_id": profile_id},
        json={"asset_id": asset["id"]},
        headers=_auth_headers(tokens),
    )
    assert extra_evidence.status_code == 409


def test_verification_request_not_owned_is_404(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "verify-d@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "verify-e@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    created = client.post(
        f"/v1/profiles/{a_profile}/verification-requests",
        json={"check_type": "phone"},
        headers=_auth_headers(a_tokens),
    ).json()

    resp = client.get(
        f"/v1/verification-requests/{created['id']}",
        params={"acting_profile_id": b_profile},
        headers=_auth_headers(b_tokens),
    )
    assert resp.status_code == 404


def test_verification_claims_empty_by_default(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "verify-f@example.com", "correct horse battery")
    a_profile = _create_profile(a_tokens)
    b_tokens = _register_verify_login(monkeypatch, "verify-g@example.com", "correct horse battery")
    b_profile = _create_profile(b_tokens)

    resp = client.get(
        f"/v1/profiles/{b_profile}/verification-claims",
        params={"acting_profile_id": a_profile},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ---- Moderation appeals -----------------------------------------------------


def test_moderation_appeal_happy_path_and_overwrite(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "appeal-a@example.com", "correct horse battery")
    login_resp = client.post(
        "/v1/auth/login", json={"email": "appeal-a@example.com", "password": "correct horse battery"}
    )
    assert login_resp.status_code == 200

    # Look up the caller's account id via a manager-visible profile call is
    # not exposed directly; the JWT `sub` claim is the account id, decoded
    # the same way `get_current_session` does, to seed a matching action.
    import jwt

    from app.core.config import get_settings

    payload = jwt.decode(
        tokens["access_token"], get_settings().jwt_secret, algorithms=["HS256"]
    )
    account_id = payload["sub"]

    action = moderation_actions_repo.create_action(account_id, "profile_suspended", "policy violation")

    resp = client.post(
        f"/v1/moderation-actions/{action['id']}/appeals",
        json={"reason": "This was a mistake."},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "queued"

    # Resubmission overwrites (idempotent upsert).
    resp2 = client.post(
        f"/v1/moderation-actions/{action['id']}/appeals",
        json={"reason": "Updated reason."},
        headers=_auth_headers(tokens),
    )
    assert resp2.status_code == 202
    assert resp2.json()["reason"] == "Updated reason."


def test_moderation_appeal_wrong_account_is_404(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "appeal-b@example.com", "correct horse battery")
    b_tokens = _register_verify_login(monkeypatch, "appeal-c@example.com", "correct horse battery")

    action = moderation_actions_repo.create_action("some-other-account-id", "profile_suspended", "x")

    resp = client.post(
        f"/v1/moderation-actions/{action['id']}/appeals",
        json={"reason": "Not mine."},
        headers=_auth_headers(a_tokens),
    )
    assert resp.status_code == 404

    resp2 = client.post(
        f"/v1/moderation-actions/{action['id']}/appeals",
        json={"reason": "Not mine either."},
        headers=_auth_headers(b_tokens),
    )
    assert resp2.status_code == 404


def test_moderation_appeal_unknown_action_is_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "appeal-d@example.com", "correct horse battery")

    resp = client.post(
        "/v1/moderation-actions/does-not-exist/appeals",
        json={"reason": "n/a"},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 404
