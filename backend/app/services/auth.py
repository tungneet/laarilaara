"""Authentication application services."""
from __future__ import annotations

import uuid

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.accounts import Account, AccountStatus
from app.repositories import accounts as accounts_repo
from app.repositories import challenges as challenges_repo
from app.repositories import sessions as sessions_repo
from app.services.notifications import (
    generate_numeric_code,
    is_phone_number,
    send_verification_code,
)

logger = get_logger(__name__)


class InvalidCredentialsError(Exception):
    pass


class AccountNotVerifiedError(Exception):
    pass


class PhoneNumberInvalidError(Exception):
    """The supplied phone number isn't a plausible E.164 number
    (e.g. +14155550123)."""


class GoogleTokenInvalidError(Exception):
    """The Google ID token failed signature/audience/expiry verification, or
    Google reports the token's email as unverified."""


def register_account(
    email: str,
    password: str,
    locale: str = "en",
    display_name: str | None = None,
    gender: str | None = None,
) -> str:
    """Start registration.

    Always returns a challenge_id (same one for new and existing emails, never reveals
    whether the email already existed, so the endpoint response cannot be used to
    enumerate accounts). On a genuinely new email an account plus an email-verification
    challenge are created. On an existing email, a fake challenge_id is returned that
    will fail verification.
    """
    password_hash = hash_password(password)
    try:
        account = accounts_repo.create_account(
            email=email,
            password_hash=password_hash,
            locale=locale,
            display_name=display_name,
            gender=gender,
        )
    except accounts_repo.EmailAlreadyRegisteredError:
        # Silent: do not reveal existence. A real system may send a
        # "you already have an account" email out-of-band here.
        logger.info("registration attempted for existing email (suppressed)")
        # Return a fake challenge_id that looks real but will fail verification
        return str(uuid.uuid4())

    code = generate_numeric_code()
    challenge = challenges_repo.create_email_verification_challenge(account.id, code)
    send_verification_code(account.email, code, challenge.id)
    return challenge.id


def verify_challenge(challenge_id: str, code: str) -> None:
    """Verify an email-verification challenge and activate the account.

    Raises ``challenges_repo.ChallengeNotFoundError`` or
    ``challenges_repo.ChallengeInvalidError`` on any failure; the router maps
    both to the same generic error response.
    """
    account_id, _ = challenges_repo.verify_and_consume(
        challenge_id, code, expected_purpose="email_verification"
    )
    accounts_repo.mark_account_active(account_id)


def _issue_session(account: Account) -> tuple[str, str, int]:
    session_id, refresh_token = sessions_repo.create_session(account.id)
    access_token, expires_in = create_access_token(
        account_id=account.id, session_id=session_id, tier=account.tier.value, role=account.role.value
    )
    return access_token, refresh_token, expires_in


def login(email: str, password: str) -> tuple[str, str, int]:
    """Verify credentials and issue a new session.

    Returns (access_token, refresh_token, expires_in_seconds). Raises
    ``InvalidCredentialsError`` for an unknown email or wrong password (kept
    indistinguishable to avoid enumeration), or ``AccountNotVerifiedError`` for
    a correct password on an account that has not completed email
    verification yet (not an enumeration risk: the caller already proved they
    hold the password).
    """
    credentials = accounts_repo.get_credentials_by_email(email)
    if credentials is None:
        raise InvalidCredentialsError()

    account, password_hash = credentials
    if not verify_password(password, password_hash):
        raise InvalidCredentialsError()

    if account.status != AccountStatus.ACTIVE:
        raise AccountNotVerifiedError()

    return _issue_session(account)


def login_with_google(google_id_token_value: str) -> tuple[str, str, int]:
    """Verify a Google Identity Services ID token and issue a session.

    First sign-in for a given email creates a new, immediately-``active``
    account (Google already verified the email address, so our own
    email-verification challenge is skipped). A later Google sign-in with an
    email that already has a (e.g. password-based) account simply links that
    account to this Google identity rather than creating a duplicate.

    Raises ``GoogleTokenInvalidError`` if the token doesn't verify or its
    email is unverified per Google.
    """
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise GoogleTokenInvalidError("Google sign-in is not configured")

    try:
        payload = google_id_token.verify_oauth2_token(
            google_id_token_value,
            google_requests.Request(),
            audience=settings.google_oauth_client_id,
        )
    except Exception as exc:  # noqa: BLE001 - any verification failure is the same generic error
        raise GoogleTokenInvalidError(str(exc)) from exc

    if not payload.get("email_verified", False):
        raise GoogleTokenInvalidError("Google account email is not verified")

    email = payload["email"]
    subject = payload["sub"]
    display_name = payload.get("name")

    account_id = accounts_repo.get_account_id_by_email(email)
    if account_id is None:
        account = accounts_repo.create_oauth_account(
            email=email,
            oauth_provider="google",
            oauth_subject=subject,
            display_name=display_name,
        )
        return _issue_session(account)

    account = accounts_repo.get_account_by_id(account_id)
    if account is None:
        raise GoogleTokenInvalidError("account lookup failed")

    if account.oauth_provider != "google":
        accounts_repo.set_oauth_identity(account.id, "google", subject)
    if account.status != AccountStatus.ACTIVE:
        accounts_repo.mark_account_active(account.id)
        account = accounts_repo.get_account_by_id(account.id)

    return _issue_session(account)


def start_phone_auth(phone: str) -> str:
    """Start phone sign-in/signup. Always returns a challenge_id (no enumeration of whether
    the phone is already registered), same generic-response convention as
    `register_account`.

    Phone auth has no password step at all — it's OTP-only, for both a
    brand-new phone number (implicitly creates the account) and a returning
    one (just issues a fresh login code). Raises ``PhoneNumberInvalidError``
    if the number isn't a plausible E.164 number (a client-side format
    mistake, not an enumeration risk — checked before any account lookup).
    """
    normalized = phone.strip()
    if not is_phone_number(normalized):
        raise PhoneNumberInvalidError(phone)

    account_id = accounts_repo.get_account_id_by_phone(normalized)
    if account_id is None:
        account = accounts_repo.create_phone_account(normalized)
    else:
        account = accounts_repo.get_account_by_id(account_id)
        if account is None:
            raise PhoneNumberInvalidError(phone)

    code = generate_numeric_code()
    challenge = challenges_repo.create_phone_auth_challenge(account.id, code)
    send_verification_code(normalized, code, challenge.id)
    return challenge.id


def verify_phone_and_login(challenge_id: str, code: str) -> tuple[str, str, int]:
    """Verify a phone-auth code and issue a session — this IS the login step
    for phone sign-in (there's no separate password to check afterwards).

    Raises ``challenges_repo.ChallengeNotFoundError``/``ChallengeInvalidError``
    on any failure, same as email-challenge verification; the router maps
    both to the same generic error response.
    """
    account_id, _ = challenges_repo.verify_and_consume(
        challenge_id, code, expected_purpose="phone_auth"
    )
    account = accounts_repo.get_account_by_id(account_id)
    if account is None:
        raise challenges_repo.ChallengeInvalidError("account_missing")
    if account.status != AccountStatus.ACTIVE:
        accounts_repo.mark_account_active(account.id)
        account = accounts_repo.get_account_by_id(account.id)

    return _issue_session(account)


def refresh(refresh_token: str) -> tuple[str, str, int]:
    """Rotate a refresh token and issue a fresh access token.

    Raises ``sessions_repo.RefreshTokenInvalidError`` on any failure
    (unknown/expired/revoked/already-rotated-away token); the router maps this
    to a single generic error response.
    """
    account_id, new_session_id, new_refresh_token = sessions_repo.rotate_session(
        refresh_token
    )
    account = accounts_repo.get_account_by_id(account_id)
    if account is None or account.status != AccountStatus.ACTIVE:
        raise sessions_repo.RefreshTokenInvalidError("account_not_active")

    access_token, expires_in = create_access_token(
        account_id=account.id, session_id=new_session_id, tier=account.tier.value, role=account.role.value
    )
    return access_token, new_refresh_token, expires_in


def logout(account_id: str, session_id: str) -> None:
    sessions_repo.revoke_session(account_id, session_id)


def logout_all(account_id: str) -> None:
    sessions_repo.revoke_all_sessions(account_id)


def request_password_reset(email: str) -> None:
    """Start a password reset. Always returns, regardless of whether the
    email exists, to avoid enumeration."""
    account_id = accounts_repo.get_account_id_by_email(email)
    if account_id is None:
        logger.info("password reset requested for unknown email (suppressed)")
        return

    code = generate_numeric_code()
    challenge = challenges_repo.create_password_reset_challenge(account_id, code)
    send_verification_code(email, code, challenge.id)


def reset_password(challenge_id: str, code: str, new_password: str) -> None:
    """Verify a password-reset challenge and set the new password.

    Also revokes all existing sessions, since a password reset should log out
    any other holder of the old credentials.
    """
    account_id, _ = challenges_repo.verify_and_consume(
        challenge_id, code, expected_purpose="password_reset"
    )
    password_hash = hash_password(new_password)
    accounts_repo.set_password_hash(account_id, password_hash)
    sessions_repo.revoke_all_sessions(account_id)
