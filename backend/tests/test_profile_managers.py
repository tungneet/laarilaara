"""Tests for /v1/profiles managers, manager-invitations, and candidate-consent
(catalog §5 — "Managers and consent" block)."""
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


def _create_profile(tokens: dict, relationship: str = "self") -> str:
    resp = client.post(
        "/v1/profiles", json={"relationship": relationship}, headers=_auth_headers(tokens)
    )
    return resp.json()["id"]


def test_list_managers_shows_owner_only_initially(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "mgr1@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.get(f"/v1/profiles/{profile_id}/managers", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["managers"]) == 1
    assert body["managers"][0]["role"] == "owner"
    assert body["pending_invitations"] == []


def test_invite_accept_and_list_manager_flow(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "mgr2owner@example.com", "correct horse battery")
    invitee_tokens = _register_verify_login(monkeypatch, "mgr2invitee@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    captured: dict[str, str] = {}

    def fake_send(email: str, token: str, invitation_id: str) -> None:
        captured["token"] = token

    monkeypatch.setattr("app.services.profile_managers.send_manager_invitation", fake_send)

    invite_resp = client.post(
        f"/v1/profiles/{profile_id}/manager-invitations",
        json={
            "invited_email": "mgr2invitee@example.com",
            "role": "collaborator",
            "permissions": ["profile.read_private"],
        },
        headers=_auth_headers(owner_tokens),
    )
    assert invite_resp.status_code == 201
    assert invite_resp.json()["invited_email"] == "m***@example.com"

    list_resp = client.get(
        f"/v1/profiles/{profile_id}/managers", headers=_auth_headers(owner_tokens)
    )
    assert len(list_resp.json()["pending_invitations"]) == 1

    accept_resp = client.post(
        f"/v1/profile-manager-invitations/{captured['token']}/accept",
        headers=_auth_headers(invitee_tokens),
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["role"] == "collaborator"

    list_after = client.get(
        f"/v1/profiles/{profile_id}/managers", headers=_auth_headers(owner_tokens)
    )
    assert len(list_after.json()["managers"]) == 2
    assert list_after.json()["pending_invitations"] == []


def test_accept_invitation_rejects_email_mismatch(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "mgr3owner@example.com", "correct horse battery")
    wrong_tokens = _register_verify_login(monkeypatch, "mgr3wrong@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.profile_managers.send_manager_invitation",
        lambda email, token, invitation_id: captured.update(token=token),
    )
    client.post(
        f"/v1/profiles/{profile_id}/manager-invitations",
        json={"invited_email": "mgr3invitee@example.com", "role": "collaborator", "permissions": []},
        headers=_auth_headers(owner_tokens),
    )

    resp = client.post(
        f"/v1/profile-manager-invitations/{captured['token']}/accept",
        headers=_auth_headers(wrong_tokens),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PROFILE_INVITATION_EMAIL_MISMATCH"


def test_accept_unknown_token_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "mgr4@example.com", "correct horse battery")

    resp = client.post(
        "/v1/profile-manager-invitations/does-not-exist/accept", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_INVITATION_NOT_FOUND"


def test_patch_manager_updates_permissions_and_exclusive_primary(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "mgr5owner@example.com", "correct horse battery")
    invitee_tokens = _register_verify_login(monkeypatch, "mgr5invitee@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.profile_managers.send_manager_invitation",
        lambda email, token, invitation_id: captured.update(token=token),
    )
    client.post(
        f"/v1/profiles/{profile_id}/manager-invitations",
        json={"invited_email": "mgr5invitee@example.com", "role": "collaborator", "permissions": []},
        headers=_auth_headers(owner_tokens),
    )
    client.post(
        f"/v1/profile-manager-invitations/{captured['token']}/accept",
        headers=_auth_headers(invitee_tokens),
    )
    invitee_account_id = client.get(
        "/v1/me", headers=_auth_headers(invitee_tokens)
    ).json()["id"]

    patch_resp = client.patch(
        f"/v1/profiles/{profile_id}/managers/{invitee_account_id}",
        json={"permissions": ["profile.read_private", "profile.edit"], "is_primary": True},
        headers=_auth_headers(owner_tokens),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_primary"] is True
    assert "profile.edit" in patch_resp.json()["permissions"]

    managers = client.get(
        f"/v1/profiles/{profile_id}/managers", headers=_auth_headers(owner_tokens)
    ).json()["managers"]
    owner_entry = next(m for m in managers if m["role"] == "owner")
    assert owner_entry["is_primary"] is False


def test_cannot_revoke_last_manager(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "mgr6@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)
    account_id = client.get("/v1/me", headers=_auth_headers(tokens)).json()["id"]

    resp = client.delete(
        f"/v1/profiles/{profile_id}/managers/{account_id}", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "PROFILE_CANNOT_ORPHAN"


def test_revoke_manager_success_when_not_last(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "mgr7owner@example.com", "correct horse battery")
    invitee_tokens = _register_verify_login(monkeypatch, "mgr7invitee@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens)

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.profile_managers.send_manager_invitation",
        lambda email, token, invitation_id: captured.update(token=token),
    )
    client.post(
        f"/v1/profiles/{profile_id}/manager-invitations",
        json={"invited_email": "mgr7invitee@example.com", "role": "collaborator", "permissions": []},
        headers=_auth_headers(owner_tokens),
    )
    client.post(
        f"/v1/profile-manager-invitations/{captured['token']}/accept",
        headers=_auth_headers(invitee_tokens),
    )
    invitee_account_id = client.get("/v1/me", headers=_auth_headers(invitee_tokens)).json()["id"]

    resp = client.delete(
        f"/v1/profiles/{profile_id}/managers/{invitee_account_id}",
        headers=_auth_headers(owner_tokens),
    )
    assert resp.status_code == 204


def test_manager_not_found_returns_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "mgr8@example.com", "correct horse battery")
    profile_id = _create_profile(tokens)

    resp = client.delete(
        f"/v1/profiles/{profile_id}/managers/unknown-account", headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_MANAGER_NOT_FOUND"


def test_candidate_consent_allowed_for_self_owner(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "mgr9@example.com", "correct horse battery")
    profile_id = _create_profile(tokens, relationship="self")

    resp = client.post(
        f"/v1/profiles/{profile_id}/candidate-consent",
        json={"decision": "publish_authorized", "granted": True},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 201
    assert resp.json()["granted"] is True
    assert resp.json()["decision"] == "publish_authorized"


def test_candidate_consent_forbidden_for_other_relationship_owner(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "mgr10@example.com", "correct horse battery")
    profile_id = _create_profile(tokens, relationship="other")

    resp = client.post(
        f"/v1/profiles/{profile_id}/candidate-consent",
        json={"decision": "publish_authorized", "granted": True},
        headers=_auth_headers(tokens),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "PROFILE_CANDIDATE_CONSENT_FORBIDDEN"


def test_candidate_consent_allowed_for_accepted_candidate_role(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "mgr11owner@example.com", "correct horse battery")
    candidate_tokens = _register_verify_login(monkeypatch, "mgr11candidate@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens, relationship="other")

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.profile_managers.send_manager_invitation",
        lambda email, token, invitation_id: captured.update(token=token),
    )
    client.post(
        f"/v1/profiles/{profile_id}/manager-invitations",
        json={"invited_email": "mgr11candidate@example.com", "role": "candidate", "permissions": []},
        headers=_auth_headers(owner_tokens),
    )
    client.post(
        f"/v1/profile-manager-invitations/{captured['token']}/accept",
        headers=_auth_headers(candidate_tokens),
    )

    resp = client.post(
        f"/v1/profiles/{profile_id}/candidate-consent",
        json={"decision": "publish_authorized", "granted": True},
        headers=_auth_headers(candidate_tokens),
    )
    assert resp.status_code == 201


def test_cannot_revoke_candidate_manager(dynamo_table, monkeypatch):
    owner_tokens = _register_verify_login(monkeypatch, "mgr12owner@example.com", "correct horse battery")
    candidate_tokens = _register_verify_login(monkeypatch, "mgr12candidate@example.com", "correct horse battery")
    profile_id = _create_profile(owner_tokens, relationship="other")

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        "app.services.profile_managers.send_manager_invitation",
        lambda email, token, invitation_id: captured.update(token=token),
    )
    client.post(
        f"/v1/profiles/{profile_id}/manager-invitations",
        json={"invited_email": "mgr12candidate@example.com", "role": "candidate", "permissions": []},
        headers=_auth_headers(owner_tokens),
    )
    client.post(
        f"/v1/profile-manager-invitations/{captured['token']}/accept",
        headers=_auth_headers(candidate_tokens),
    )
    candidate_account_id = client.get(
        "/v1/me", headers=_auth_headers(candidate_tokens)
    ).json()["id"]

    resp = client.delete(
        f"/v1/profiles/{profile_id}/managers/{candidate_account_id}",
        headers=_auth_headers(owner_tokens),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "PROFILE_CANNOT_REVOKE_CANDIDATE"


def test_managers_endpoints_require_bearer_token(dynamo_table):
    resp = client.get("/v1/profiles/some-id/managers")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"
