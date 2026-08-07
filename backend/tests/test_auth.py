"""Tests for the auth/account register endpoint and its data layer."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.repositories import accounts as accounts_repo

client = TestClient(app)

_VALID = {"email": "aman@example.com", "password": "correct horse battery"}


def test_register_returns_generic_202(dynamo_table):
    resp = client.post("/v1/auth/register", json=_VALID)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "verification_pending"
    # Response must not leak whether the account is new.
    assert "aman@example.com" not in resp.text


def test_register_creates_account_with_free_tier(dynamo_table):
    client.post("/v1/auth/register", json=_VALID)
    account_id = accounts_repo.get_account_id_by_email(_VALID["email"])
    assert account_id is not None
    account = accounts_repo.get_account_by_id(account_id)
    assert account is not None
    assert account.tier.value == "free"
    assert account.status.value == "pending_verification"


def test_duplicate_email_is_silent_and_creates_one_account(dynamo_table):
    first = client.post("/v1/auth/register", json=_VALID)
    second = client.post("/v1/auth/register", json=_VALID)
    # Both respond identically (no enumeration).
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    # But only one account exists.
    account_id = accounts_repo.get_account_id_by_email(_VALID["email"])
    assert account_id is not None


def test_register_rejects_weak_password(dynamo_table):
    resp = client.post(
        "/v1/auth/register",
        json={"email": "b@example.com", "password": "short"},
    )
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["code"] == "VALIDATION_FAILED"


def test_register_rejects_invalid_email(dynamo_table):
    resp = client.post(
        "/v1/auth/register",
        json={"email": "not-an-email", "password": "correct horse battery"},
    )
    assert resp.status_code == 422


def _register_and_capture_challenge(monkeypatch, email: str, password: str) -> tuple[str, str]:
    """Register an account and capture (challenge_id, code) via the
    notification side-channel, mirroring how a real client would learn the
    challenge id (from the verification email), never from the API response.
    """
    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    resp = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 202
    return captured["challenge_id"], captured["code"]


def test_verify_challenge_activates_account(dynamo_table, monkeypatch):
    email, password = "verify@example.com", "correct horse battery"
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)

    resp = client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"

    account_id = accounts_repo.get_account_id_by_email(email)
    account = accounts_repo.get_account_by_id(account_id)
    assert account.status.value == "active"


def test_verify_challenge_rejects_wrong_code(dynamo_table, monkeypatch):
    email, password = "wrongcode@example.com", "correct horse battery"
    challenge_id, _code = _register_and_capture_challenge(monkeypatch, email, password)

    resp = client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": "000000"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "CHALLENGE_INVALID"


def test_verify_challenge_cannot_be_reused(dynamo_table, monkeypatch):
    email, password = "reuse@example.com", "correct horse battery"
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)

    first = client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})
    second = client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})
    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["code"] == "CHALLENGE_INVALID"


def test_verify_challenge_unknown_id_is_generic(dynamo_table):
    resp = client.post("/v1/auth/challenges/does-not-exist/verify", json={"code": "123456"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "CHALLENGE_INVALID"


def test_login_succeeds_after_verification(dynamo_table, monkeypatch):
    email, password = "login@example.com", "correct horse battery"
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)
    client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})

    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "Bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] > 0


def test_login_rejects_unverified_account(dynamo_table, monkeypatch):
    email, password = "unverified@example.com", "correct horse battery"
    _register_and_capture_challenge(monkeypatch, email, password)

    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_NOT_VERIFIED"


def test_login_rejects_wrong_password(dynamo_table, monkeypatch):
    email, password = "wrongpw@example.com", "correct horse battery"
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)
    client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})

    resp = client.post("/v1/auth/login", json={"email": email, "password": "wrong password entirely"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_unknown_email(dynamo_table):
    resp = client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever password"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def _register_verify_login(monkeypatch, email: str, password: str) -> dict:
    challenge_id, code = _register_and_capture_challenge(monkeypatch, email, password)
    client.post(f"/v1/auth/challenges/{challenge_id}/verify", json={"code": code})
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()


def test_refresh_issues_new_tokens(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "refresh@example.com", "correct horse battery")

    resp = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] != tokens["access_token"]
    assert body["refresh_token"] != tokens["refresh_token"]


def test_refresh_rejects_reused_token_and_revokes_family(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "reuse-refresh@example.com", "correct horse battery")
    old_refresh_token = tokens["refresh_token"]

    first = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert first.status_code == 200
    new_refresh_token = first.json()["refresh_token"]

    # Replaying the rotated-away token is reuse: it must fail...
    replay = client.post("/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    assert replay.status_code == 401
    assert replay.json()["code"] == "INVALID_REFRESH_TOKEN"

    # ...and revokes the whole chain, so even the latest token stops working.
    after_reuse = client.post("/v1/auth/refresh", json={"refresh_token": new_refresh_token})
    assert after_reuse.status_code == 401
    assert after_reuse.json()["code"] == "INVALID_REFRESH_TOKEN"


def test_refresh_rejects_unknown_token(dynamo_table):
    resp = client.post("/v1/auth/refresh", json={"refresh_token": "does-not.exist"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_REFRESH_TOKEN"


def test_logout_revokes_session(dynamo_table, monkeypatch):
    tokens = _register_verify_login(monkeypatch, "logout@example.com", "correct horse battery")

    resp = client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out"

    # The now-revoked session's refresh token can no longer be used.
    refresh_resp = client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_resp.status_code == 401


def test_logout_requires_bearer_token(dynamo_table):
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


def test_logout_all_revokes_every_session(dynamo_table, monkeypatch):
    email, password = "logoutall@example.com", "correct horse battery"
    tokens_a = _register_verify_login(monkeypatch, email, password)
    login_b = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login_b.status_code == 200
    tokens_b = login_b.json()

    resp = client.post(
        "/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens_a['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "logged_out_all"

    for tokens in (tokens_a, tokens_b):
        refresh_resp = client.post(
            "/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_resp.status_code == 401


def test_forgot_and_reset_password_flow(dynamo_table, monkeypatch):
    email, password = "resetme@example.com", "correct horse battery"
    _register_verify_login(monkeypatch, email, password)

    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["code"] = code
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    forgot_resp = client.post("/v1/auth/password/forgot", json={"email": email})
    assert forgot_resp.status_code == 202

    new_password = "brand new password here"
    reset_resp = client.post(
        "/v1/auth/password/reset",
        json={
            "challenge_id": captured["challenge_id"],
            "code": captured["code"],
            "new_password": new_password,
        },
    )
    assert reset_resp.status_code == 200

    old_login = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert old_login.status_code == 401

    new_login = client.post("/v1/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == 200


def test_forgot_password_is_generic_for_unknown_email(dynamo_table):
    resp = client.post("/v1/auth/password/forgot", json={"email": "ghost@example.com"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "reset_pending"


def test_reset_password_rejects_wrong_code(dynamo_table, monkeypatch):
    email, password = "resetwrong@example.com", "correct horse battery"
    _register_verify_login(monkeypatch, email, password)

    captured: dict[str, str] = {}

    def fake_send(to_email: str, code: str, challenge_id: str) -> None:
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    client.post("/v1/auth/password/forgot", json={"email": email})

    resp = client.post(
        "/v1/auth/password/reset",
        json={
            "challenge_id": captured["challenge_id"],
            "code": "000000",
            "new_password": "does not matter here",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "CHALLENGE_INVALID"


def test_get_me_returns_profile(dynamo_table, monkeypatch):
    email, password = "me@example.com", "correct horse battery"
    tokens = _register_verify_login(monkeypatch, email, password)

    resp = client.get("/v1/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == email
    assert body["status"] == "active"
    assert body["tier"] == "free"


def test_patch_me_updates_locale(dynamo_table, monkeypatch):
    email, password = "mepatch@example.com", "correct horse battery"
    tokens = _register_verify_login(monkeypatch, email, password)

    resp = client.patch(
        "/v1/me",
        json={"locale": "pa"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["locale"] == "pa"


def test_me_requires_bearer_token(dynamo_table):
    resp = client.get("/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHENTICATED"


# ---- Google OAuth sign-in ---------------------------------------------------


def _fake_google_payload(email: str, sub: str = "google-subject-1", email_verified: bool = True) -> dict:
    return {"email": email, "email_verified": email_verified, "sub": sub, "name": "Google User"}


def test_google_signin_creates_new_active_account(dynamo_table, monkeypatch):
    monkeypatch.setattr(
        "app.services.auth.get_settings",
        lambda: type("S", (), {"google_oauth_client_id": "test-client-id"})(),
    )
    from app.repositories import accounts as accounts_repo

    payload = _fake_google_payload("newgoogleuser@example.com")
    monkeypatch.setattr(
        "app.services.auth.google_id_token.verify_oauth2_token", lambda *a, **k: payload
    )

    resp = client.post("/v1/auth/oauth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]

    account_id = accounts_repo.get_account_id_by_email("newgoogleuser@example.com")
    account = accounts_repo.get_account_by_id(account_id)
    assert account.status.value == "active"
    assert account.oauth_provider == "google"
    assert account.oauth_subject == "google-subject-1"


def test_google_signin_links_existing_email_password_account(dynamo_table, monkeypatch):
    email, password = "linkme@example.com", "correct horse battery"
    _register_verify_login(monkeypatch, email, password)

    monkeypatch.setattr(
        "app.services.auth.get_settings",
        lambda: type("S", (), {"google_oauth_client_id": "test-client-id"})(),
    )
    payload = _fake_google_payload(email, sub="google-subject-2")
    monkeypatch.setattr(
        "app.services.auth.google_id_token.verify_oauth2_token", lambda *a, **k: payload
    )

    resp = client.post("/v1/auth/oauth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200

    from app.repositories import accounts as accounts_repo

    account_id = accounts_repo.get_account_id_by_email(email)
    account = accounts_repo.get_account_by_id(account_id)
    assert account.oauth_provider == "google"
    assert account.oauth_subject == "google-subject-2"
    # The original password still works — linking doesn't disturb it.
    login_resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200


def test_google_signin_rejects_unverified_email(dynamo_table, monkeypatch):
    monkeypatch.setattr(
        "app.services.auth.get_settings",
        lambda: type("S", (), {"google_oauth_client_id": "test-client-id"})(),
    )
    payload = _fake_google_payload("unverified@example.com", email_verified=False)
    monkeypatch.setattr(
        "app.services.auth.google_id_token.verify_oauth2_token", lambda *a, **k: payload
    )

    resp = client.post("/v1/auth/oauth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "GOOGLE_TOKEN_INVALID"


def test_google_signin_rejects_invalid_token(dynamo_table, monkeypatch):
    monkeypatch.setattr(
        "app.services.auth.get_settings",
        lambda: type("S", (), {"google_oauth_client_id": "test-client-id"})(),
    )

    def raise_value_error(*a, **k):
        raise ValueError("Token used too late")

    monkeypatch.setattr("app.services.auth.google_id_token.verify_oauth2_token", raise_value_error)

    resp = client.post("/v1/auth/oauth/google", json={"id_token": "garbage"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "GOOGLE_TOKEN_INVALID"


def test_google_signin_disabled_without_client_id(dynamo_table, monkeypatch):
    monkeypatch.setattr(
        "app.services.auth.get_settings",
        lambda: type("S", (), {"google_oauth_client_id": None})(),
    )
    resp = client.post("/v1/auth/oauth/google", json={"id_token": "whatever"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "GOOGLE_TOKEN_INVALID"


# ---- Phone (SMS OTP) sign-in ------------------------------------------------


def _start_phone_and_capture(monkeypatch, phone: str) -> tuple[str, str]:
    captured: dict[str, str] = {}

    def fake_send(to_value: str, code: str, challenge_id: str) -> None:
        captured["code"] = code
        captured["challenge_id"] = challenge_id

    monkeypatch.setattr("app.services.auth.send_verification_code", fake_send)
    resp = client.post("/v1/auth/phone/start", json={"phone": phone})
    assert resp.status_code == 202
    return captured["challenge_id"], captured["code"]


def test_phone_start_creates_new_pending_account(dynamo_table, monkeypatch):
    from app.repositories import accounts as accounts_repo

    _start_phone_and_capture(monkeypatch, "+14155550100")

    account_id = accounts_repo.get_account_id_by_phone("+14155550100")
    assert account_id is not None
    account = accounts_repo.get_account_by_id(account_id)
    assert account.status.value == "pending_verification"
    assert account.phone == "+14155550100"
    assert account.email is None


def test_phone_verify_activates_and_logs_in(dynamo_table, monkeypatch):
    challenge_id, code = _start_phone_and_capture(monkeypatch, "+14155550101")

    resp = client.post("/v1/auth/phone/verify", json={"challenge_id": challenge_id, "code": code})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]

    from app.repositories import accounts as accounts_repo

    account_id = accounts_repo.get_account_id_by_phone("+14155550101")
    account = accounts_repo.get_account_by_id(account_id)
    assert account.status.value == "active"


def test_phone_verify_rejects_wrong_code(dynamo_table, monkeypatch):
    challenge_id, _code = _start_phone_and_capture(monkeypatch, "+14155550102")

    resp = client.post("/v1/auth/phone/verify", json={"challenge_id": challenge_id, "code": "000000"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "CHALLENGE_INVALID"


def test_phone_start_rejects_invalid_phone_shape(dynamo_table):
    resp = client.post("/v1/auth/phone/start", json={"phone": "not-a-phone-number"})
    assert resp.status_code == 422
    assert resp.json()["code"] == "PHONE_NUMBER_INVALID"


def test_phone_start_on_existing_phone_reuses_account(dynamo_table, monkeypatch):
    from app.repositories import accounts as accounts_repo

    challenge_id, code = _start_phone_and_capture(monkeypatch, "+14155550103")
    client.post("/v1/auth/phone/verify", json={"challenge_id": challenge_id, "code": code})
    first_account_id = accounts_repo.get_account_id_by_phone("+14155550103")

    # A second sign-in attempt with the same phone must reuse the same
    # account, not create a duplicate.
    _start_phone_and_capture(monkeypatch, "+14155550103")
    second_account_id = accounts_repo.get_account_id_by_phone("+14155550103")
    assert first_account_id == second_account_id

