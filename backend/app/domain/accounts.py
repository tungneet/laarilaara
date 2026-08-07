"""Account domain models.

The ``tier`` field is the anchor for the future freemium/premium model. It
defaults to ``free`` and is read by the entitlements seam. Payments and real
per-tier limits are deferred; nothing here depends on a payment provider.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class AccountStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETION_REQUESTED = "deletion_requested"


class AccountTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"


class AccountRole(str, Enum):
    """Authorization role, anchor for catalog §15's admin surface.

    Defaults to ``member`` for every self-registered account; there is no
    self-serve or API path to become ``admin`` (matches the "no creation
    endpoint" gap seen elsewhere) — an admin role can only be granted by a
    direct repository call (`accounts_repo.set_role`), used by ops tooling
    and by tests that need an admin session.
    """

    MEMBER = "member"
    ADMIN = "admin"


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Account(BaseModel):
    id: str
    # Exactly one of email/phone is guaranteed to be set (whichever the
    # account was created with) — both optional so phone-only accounts
    # don't need a placeholder email, and vice versa.
    email: str | None = None
    phone: str | None = None
    display_name: str | None = None
    gender: str | None = None
    # Set when the account was created via (or later linked to) an OAuth
    # provider, e.g. "google". `oauth_subject` is that provider's stable
    # user id (Google's `sub` claim) — used to detect the same external
    # identity even if the account's email address later changes.
    oauth_provider: str | None = None
    oauth_subject: str | None = None
    status: AccountStatus = AccountStatus.PENDING_VERIFICATION
    tier: AccountTier = AccountTier.FREE
    role: AccountRole = AccountRole.MEMBER
    locale: str = "en"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
