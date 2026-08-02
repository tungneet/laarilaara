"""Authentication application services."""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.accounts import AccountStatus
from app.repositories import accounts as accounts_repo
from app.repositories import challenges as challenges_repo
from app.repositories import sessions as sessions_repo
from app.services.notifications import (
    generate_numeric_code,
    send_verification_code,
)

logger = get_logger(__name__)


class InvalidCredentialsError(Exception):
    pass


class AccountNotVerifiedError(Exception):
    pass


def register_account(
    email: str,
    password: str,
    locale: str = "en",
    display_name: str | None = None,
    gender: str | None = None,
) -> None:
    """Start registration.

    Always returns without indicating whether the email already existed, so the
    endpoint response cannot be used to enumerate accounts. On a genuinely new
    email an account plus an email-verification challenge are created.
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
        return

    code = generate_numeric_code()
    challenge = challenges_repo.create_email_verification_challenge(account.id, code)
    send_verification_code(account.email, code, challenge.id)


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

    session_id, refresh_token = sessions_repo.create_session(account.id)
    access_token, expires_in = create_access_token(
        account_id=account.id, session_id=session_id, tier=account.tier.value, role=account.role.value
    )
    return access_token, refresh_token, expires_in


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
