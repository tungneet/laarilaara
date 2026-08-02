"""Tests for catalog §15 "Administrative API" (28 HTTP operations across
seven sub-areas: dashboard, accounts/profiles, moderation, verification,
billing/support, brands/config, reference data).

There is no self-serve way to become an admin (see
`app/domain/accounts.py::AccountRole`), so tests promote a normal
registered account via the white-box `accounts_repo.set_role` helper and
then re-login to obtain a fresh access token carrying the `role: "admin"`
JWT claim (role is embedded at login time, not read live per-request).

Several admin resources (moderation cases, brand/experience/feature-flag
configs) have no creation endpoint in the baseline catalog either, so tests
seed them directly via their repositories (white-box, same pattern used
throughout §11/§12/§13/§14 tests).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain.accounts import AccountRole
from app.main import app
from app.repositories import accounts as accounts_repo
from app.repositories import billing as billing_repo
from app.repositories import brand_configs as brand_configs_repo
from app.repositories import experience_configs as experience_configs_repo
from app.repositories import feature_flags as feature_flags_repo
from app.repositories import moderation_cases as moderation_cases_repo
from app.repositories import support_tickets as support_tickets_repo
from app.repositories import verification_requests as verification_requests_repo

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


def _account_id(tokens: dict) -> str:
    import jwt

    from app.core.config import get_settings

    payload = jwt.decode(tokens["access_token"], get_settings().jwt_secret, algorithms=["HS256"])
    return payload["sub"]


def _register_admin(monkeypatch, email: str, password: str) -> dict:
    """Register + verify a normal account, promote it to admin, then
    re-login so the returned tokens carry `role: "admin"`.
    """
    tokens = _register_verify_login(monkeypatch, email, password)
    account_id = _account_id(tokens)
    accounts_repo.set_role(account_id, AccountRole.ADMIN)
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


# ---- Admin-required gate -----------------------------------------------------


def test_admin_endpoint_rejects_non_admin_session(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "member@example.com", "correct horse battery")
    resp = client.get("/v1/admin/dashboard", headers=_auth_headers(tokens))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ADMIN_REQUIRED"


def test_admin_endpoint_requires_auth(dynamo_table):
    resp = client.get("/v1/admin/dashboard")
    assert resp.status_code == 401


# ---- Dashboard ----------------------------------------------------------------


def test_dashboard_counts_accounts_and_profiles(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-dash@example.com", "correct horse battery")
    resp = client.get("/v1/admin/dashboard", headers=_auth_headers(admin_tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_count"] >= 1
    assert "open_moderation_case_count" in body


def test_queue_health_reports_static_queue_list(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-queue@example.com", "correct horse battery")
    resp = client.get("/v1/admin/health/queues", headers=_auth_headers(admin_tokens))
    assert resp.status_code == 200
    names = {q["name"] for q in resp.json()["queues"]}
    assert names == {"verification-requests", "support-tickets", "moderation-cases"}


# ---- Accounts/profiles --------------------------------------------------------


def test_admin_can_list_and_get_any_account(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-accts@example.com", "correct horse battery")
    member_tokens = _register_verify_login(monkeypatch, "member-accts@example.com", "correct horse battery")
    member_id = _account_id(member_tokens)

    list_resp = client.get("/v1/admin/accounts", headers=_auth_headers(admin_tokens))
    assert list_resp.status_code == 200
    assert len(list_resp.json()["items"]) >= 2

    get_resp = client.get(f"/v1/admin/accounts/{member_id}", headers=_auth_headers(admin_tokens))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == member_id


def test_admin_get_unknown_account_is_404(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-accts2@example.com", "correct horse battery")
    resp = client.get("/v1/admin/accounts/does-not-exist", headers=_auth_headers(admin_tokens))
    assert resp.status_code == 404


def test_admin_can_list_and_get_any_profile(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-profs@example.com", "correct horse battery")
    member_tokens = _register_verify_login(monkeypatch, "member-profs@example.com", "correct horse battery")
    profile_resp = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(member_tokens)
    )
    profile_id = profile_resp.json()["id"]

    list_resp = client.get("/v1/admin/profiles", headers=_auth_headers(admin_tokens))
    assert list_resp.status_code == 200
    assert any(p["id"] == profile_id for p in list_resp.json()["items"])

    get_resp = client.get(f"/v1/admin/profiles/{profile_id}", headers=_auth_headers(admin_tokens))
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "draft"


# ---- Moderation -----------------------------------------------------------------


def test_moderation_case_assign_action_close_flow(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-mod@example.com", "correct horse battery")
    member_tokens = _register_verify_login(monkeypatch, "member-mod@example.com", "correct horse battery")
    subject_account_id = _account_id(member_tokens)
    case = moderation_cases_repo.create_case(subject_account_id)

    list_resp = client.get("/v1/admin/moderation/cases", headers=_auth_headers(admin_tokens))
    assert list_resp.status_code == 200
    assert any(c["id"] == case["id"] for c in list_resp.json()["items"])

    assign_resp = client.post(
        f"/v1/admin/moderation/cases/{case['id']}/assign",
        json={"reason": "picking up this case"},
        headers=_auth_headers(admin_tokens),
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["status"] == "assigned"

    action_resp = client.post(
        f"/v1/admin/moderation/cases/{case['id']}/actions",
        json={"action_type": "warning", "reason": "policy violation confirmed"},
        headers=_auth_headers(admin_tokens),
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["affected_account_id"] == subject_account_id

    close_resp = client.post(
        f"/v1/admin/moderation/cases/{case['id']}/close",
        json={"reason": "resolved"},
        headers=_auth_headers(admin_tokens),
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"

    reclose_resp = client.post(
        f"/v1/admin/moderation/cases/{case['id']}/close",
        json={"reason": "already closed"},
        headers=_auth_headers(admin_tokens),
    )
    assert reclose_resp.status_code == 409


def test_moderation_case_unknown_id_is_404(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-mod2@example.com", "correct horse battery")
    resp = client.post(
        "/v1/admin/moderation/cases/does-not-exist/assign",
        json={"reason": "x"},
        headers=_auth_headers(admin_tokens),
    )
    assert resp.status_code == 404


# ---- Verification -------------------------------------------------------------


def test_verification_decision_approves_and_updates_trust_summary(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-verify@example.com", "correct horse battery")
    member_tokens = _register_verify_login(monkeypatch, "member-verify@example.com", "correct horse battery")
    profile_resp = client.post(
        "/v1/profiles", json={"relationship": "self"}, headers=_auth_headers(member_tokens)
    )
    profile_id = profile_resp.json()["id"]
    created = client.post(
        f"/v1/profiles/{profile_id}/verification-requests",
        json={"check_type": "government_id"},
        headers=_auth_headers(member_tokens),
    ).json()
    request_id = created["id"]
    verification_requests_repo.mark_submitted(request_id)

    list_resp = client.get(
        "/v1/admin/verification/requests",
        params={"status": "submitted"},
        headers=_auth_headers(admin_tokens),
    )
    assert list_resp.status_code == 200
    assert any(r["id"] == request_id for r in list_resp.json()["items"])

    decide_resp = client.post(
        f"/v1/admin/verification/requests/{request_id}/decisions",
        json={"decision": "approved", "reason": "evidence checks out"},
        headers=_auth_headers(admin_tokens),
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "approved"

    redecide_resp = client.post(
        f"/v1/admin/verification/requests/{request_id}/decisions",
        json={"decision": "rejected", "reason": "changed mind"},
        headers=_auth_headers(admin_tokens),
    )
    assert redecide_resp.status_code == 409

    trust_resp = client.get(
        f"/v1/profiles/{profile_id}/trust-summary",
        params={"acting_profile_id": profile_id},
        headers=_auth_headers(member_tokens),
    )
    assert trust_resp.status_code == 200
    assert trust_resp.json()["trust_label"] == "verified"
    assert "government_id" in trust_resp.json()["verified_checks"]


# ---- Billing / support -----------------------------------------------------------


def test_admin_can_list_subscriptions_and_transactions(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-billing@example.com", "correct horse battery")
    member_tokens = _register_verify_login(monkeypatch, "member-billing@example.com", "correct horse battery")
    member_id = _account_id(member_tokens)
    billing_repo.put_subscription(member_id, "premium-monthly", "active", False)
    billing_repo.create_transaction(member_id, "charge", 999, "usd", "succeeded")

    subs_resp = client.get("/v1/admin/subscriptions", headers=_auth_headers(admin_tokens))
    assert subs_resp.status_code == 200
    assert any(s["account_id"] == member_id for s in subs_resp.json()["items"])

    txn_resp = client.get("/v1/admin/transactions", headers=_auth_headers(admin_tokens))
    assert txn_resp.status_code == 200
    assert any(t["account_id"] == member_id for t in txn_resp.json()["items"])


def test_support_ticket_create_list_get_patch_flow(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-support@example.com", "correct horse battery")

    create_resp = client.post(
        "/v1/admin/support/tickets",
        json={"subject": "cannot log in", "body": "please help"},
        headers=_auth_headers(admin_tokens),
    )
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "open"

    list_resp = client.get(
        "/v1/admin/support/tickets", params={"status": "open"}, headers=_auth_headers(admin_tokens)
    )
    assert list_resp.status_code == 200
    assert any(t["id"] == ticket_id for t in list_resp.json()["items"])

    get_resp = client.get(f"/v1/admin/support/tickets/{ticket_id}", headers=_auth_headers(admin_tokens))
    assert get_resp.status_code == 200

    patch_resp = client.patch(
        f"/v1/admin/support/tickets/{ticket_id}",
        json={"status": "closed", "reason": "resolved via email"},
        headers=_auth_headers(admin_tokens),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "closed"


def test_support_ticket_unknown_id_is_404(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-support2@example.com", "correct horse battery")
    resp = client.get("/v1/admin/support/tickets/does-not-exist", headers=_auth_headers(admin_tokens))
    assert resp.status_code == 404


# ---- Brands / experiences / feature flags -----------------------------------------


def test_brand_config_get_and_patch(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-brand@example.com", "correct horse battery")
    brand_configs_repo.seed_brand("laarilaara-punjabi", "LaariLaara Punjabi")

    get_resp = client.get("/v1/admin/brands/laarilaara-punjabi", headers=_auth_headers(admin_tokens))
    assert get_resp.status_code == 200
    assert get_resp.json()["active"] is True

    patch_resp = client.patch(
        "/v1/admin/brands/laarilaara-punjabi",
        json={"active": False, "reason": "temporarily disabling brand"},
        headers=_auth_headers(admin_tokens),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["active"] is False


def test_brand_config_unknown_id_is_404(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-brand2@example.com", "correct horse battery")
    resp = client.get("/v1/admin/brands/does-not-exist", headers=_auth_headers(admin_tokens))
    assert resp.status_code == 404


def test_experience_config_get_and_patch(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-exp@example.com", "correct horse battery")
    experience_configs_repo.seed_experience("sikh-diaspora", "Sikh Diaspora")

    get_resp = client.get("/v1/admin/experiences/sikh-diaspora", headers=_auth_headers(admin_tokens))
    assert get_resp.status_code == 200

    patch_resp = client.patch(
        "/v1/admin/experiences/sikh-diaspora",
        json={"name": "Sikh Diaspora Global", "reason": "rename"},
        headers=_auth_headers(admin_tokens),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Sikh Diaspora Global"


def test_feature_flag_get_and_patch(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-flag@example.com", "correct horse battery")
    feature_flags_repo.seed_flag("ai-icebreakers", enabled=False)

    get_resp = client.get("/v1/admin/feature-flags/ai-icebreakers", headers=_auth_headers(admin_tokens))
    assert get_resp.status_code == 200
    assert get_resp.json()["enabled"] is False

    patch_resp = client.patch(
        "/v1/admin/feature-flags/ai-icebreakers",
        json={"enabled": True, "reason": "enabling for rollout"},
        headers=_auth_headers(admin_tokens),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["enabled"] is True


def test_feature_flag_unknown_key_is_404(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-flag2@example.com", "correct horse battery")
    resp = client.get("/v1/admin/feature-flags/does-not-exist", headers=_auth_headers(admin_tokens))
    assert resp.status_code == 404


# ---- Reference data ----------------------------------------------------------------


def test_reference_data_create_list_update_deactivate_flow(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-ref@example.com", "correct horse battery")

    create_resp = client.post(
        "/v1/admin/reference/verification_checks",
        json={"id": "biometric", "label": "Biometric check", "reason": "adding new check type"},
        headers=_auth_headers(admin_tokens),
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["active"] is True

    dup_resp = client.post(
        "/v1/admin/reference/verification_checks",
        json={"id": "biometric", "label": "dup", "reason": "should fail"},
        headers=_auth_headers(admin_tokens),
    )
    assert dup_resp.status_code == 409

    list_resp = client.get(
        "/v1/admin/reference/verification_checks", headers=_auth_headers(admin_tokens)
    )
    assert list_resp.status_code == 200
    assert any(i["id"] == "biometric" for i in list_resp.json()["items"])

    update_resp = client.patch(
        "/v1/admin/reference/verification_checks/biometric",
        json={"label": "Biometric verification", "reason": "clarify label"},
        headers=_auth_headers(admin_tokens),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["label"] == "Biometric verification"

    deactivate_resp = client.post(
        "/v1/admin/reference/verification_checks/biometric/deactivate",
        json={"reason": "retiring this check"},
        headers=_auth_headers(admin_tokens),
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["active"] is False

    list_after_resp = client.get(
        "/v1/admin/reference/verification_checks", headers=_auth_headers(admin_tokens)
    )
    assert list_after_resp.json()["items"] == []

    list_include_inactive_resp = client.get(
        "/v1/admin/reference/verification_checks",
        params={"include_inactive": "true"},
        headers=_auth_headers(admin_tokens),
    )
    assert len(list_include_inactive_resp.json()["items"]) == 1


def test_reference_data_update_unknown_item_is_404(dynamo_table, monkeypatch):
    admin_tokens = _register_admin(monkeypatch, "admin-ref2@example.com", "correct horse battery")
    resp = client.patch(
        "/v1/admin/reference/plans/does-not-exist",
        json={"label": "x", "reason": "y"},
        headers=_auth_headers(admin_tokens),
    )
    assert resp.status_code == 404
