"""Tests for catalog §13 "Billing and entitlements" (7 HTTP operations).

No real payment provider or webhook worker (§14, unbuilt) is wired up —
checkout sessions never leave `status=pending`, and the subscription always
mirrors the account's own free tier since nothing ever upgrades it. Tests
seed a transaction directly via the repository (white-box, same pattern as
`test_notifications.py` seeding notifications).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import billing as billing_repo

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


# ---- Checkout sessions ------------------------------------------------------


def test_create_checkout_session_is_idempotent(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-a@example.com", "correct horse battery")

    resp1 = client.post(
        "/v1/billing/checkout-sessions", json={"plan_id": "premium-monthly"}, headers=_auth_headers(tokens)
    )
    assert resp1.status_code == 201
    body1 = resp1.json()
    assert body1["status"] == "pending"
    assert body1["plan_id"] == "premium-monthly"

    resp2 = client.post(
        "/v1/billing/checkout-sessions", json={"plan_id": "premium-monthly"}, headers=_auth_headers(tokens)
    )
    assert resp2.status_code == 201
    assert resp2.json()["id"] == body1["id"]


def test_create_checkout_session_unknown_plan_is_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-b@example.com", "correct horse battery")

    resp = client.post(
        "/v1/billing/checkout-sessions", json={"plan_id": "not-a-real-plan"}, headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404


def test_checkout_sessions_require_auth(dynamo_table):
    resp = client.post("/v1/billing/checkout-sessions", json={"plan_id": "free"})
    assert resp.status_code == 401


# ---- Subscription -----------------------------------------------------------


def test_subscription_defaults_free_and_active(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-c@example.com", "correct horse battery")

    resp = client.get("/v1/billing/subscription", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan_id"] == "free"
    assert body["status"] == "active"
    assert body["cancel_at_period_end"] is False


def test_subscription_cancel_and_resume_idempotent(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-d@example.com", "correct horse battery")

    cancel_resp = client.post("/v1/billing/subscription/cancel", headers=_auth_headers(tokens))
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["cancel_at_period_end"] is True

    # Idempotent re-cancel.
    cancel_again = client.post("/v1/billing/subscription/cancel", headers=_auth_headers(tokens))
    assert cancel_again.json()["cancel_at_period_end"] is True

    resume_resp = client.post("/v1/billing/subscription/resume", headers=_auth_headers(tokens))
    assert resume_resp.status_code == 200
    assert resume_resp.json()["cancel_at_period_end"] is False

    # Idempotent re-resume.
    resume_again = client.post("/v1/billing/subscription/resume", headers=_auth_headers(tokens))
    assert resume_again.json()["cancel_at_period_end"] is False


# ---- Transactions ------------------------------------------------------------


def test_list_transactions_newest_first_and_paginates(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-e@example.com", "correct horse battery")
    account_id = _account_id(tokens)

    for i in range(3):
        billing_repo.create_transaction(account_id, "charge", 1999 + i, "USD", "succeeded")

    resp = client.get("/v1/billing/transactions", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    assert body["items"][0]["amount_cents"] == 2001  # newest first

    page1 = client.get(
        "/v1/billing/transactions", params={"limit": 2}, headers=_auth_headers(tokens)
    ).json()
    assert len(page1["items"]) == 2
    assert page1["next_cursor"] is not None


def test_transactions_are_account_scoped(dynamo_table, monkeypatch):
    a_tokens = _register_verify_login(monkeypatch, "bill-f@example.com", "correct horse battery")
    b_tokens = _register_verify_login(monkeypatch, "bill-g@example.com", "correct horse battery")
    a_account = _account_id(a_tokens)

    billing_repo.create_transaction(a_account, "charge", 1999, "USD", "succeeded")

    b_resp = client.get("/v1/billing/transactions", headers=_auth_headers(b_tokens)).json()
    assert b_resp["items"] == []


# ---- Entitlements -------------------------------------------------------------


def test_get_entitlements_lists_all_actions_allowed(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-h@example.com", "correct horse battery")

    resp = client.get("/v1/entitlements", headers=_auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert len(body["entitlements"]) > 0
    assert all(e["allowed"] for e in body["entitlements"])


# ---- Promo redemptions ---------------------------------------------------------


def test_redeem_promo_is_idempotent(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-i@example.com", "correct horse battery")

    resp1 = client.post(
        "/v1/promo-redemptions", json={"code": "WELCOME10"}, headers=_auth_headers(tokens)
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "applied"

    resp2 = client.post(
        "/v1/promo-redemptions", json={"code": "WELCOME10"}, headers=_auth_headers(tokens)
    )
    assert resp2.status_code == 200
    assert resp2.json()["applied_at"] == resp1.json()["applied_at"]


def test_redeem_unknown_promo_is_404(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "bill-j@example.com", "correct horse battery")

    resp = client.post(
        "/v1/promo-redemptions", json={"code": "NOT-A-REAL-CODE"}, headers=_auth_headers(tokens)
    )
    assert resp.status_code == 404
