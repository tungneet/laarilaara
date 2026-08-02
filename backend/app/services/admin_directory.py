"""Admin accounts/profiles directory service (catalog §15 "Accounts/profiles").

Read-only listing/lookup that bypasses the normal per-account/per-profile
ownership restrictions everywhere else in the API — that bypass is the
entire point of this admin surface, gated by `get_current_admin_session`.
"""
from __future__ import annotations

from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.domain.accounts import Account
from app.domain.profiles import Profile
from app.repositories import accounts as accounts_repo
from app.repositories import profiles as profiles_repo


class AccountNotFoundError(Exception):
    pass


class ProfileNotFoundError(Exception):
    pass


def list_accounts(cursor: str | None, limit: int) -> dict:
    accounts = accounts_repo.list_all_accounts()
    offset = _decode_cursor(cursor)
    page = accounts[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(accounts) else None
    return {"items": page, "next_cursor": next_cursor}


def get_account(account_id: str) -> Account:
    account = accounts_repo.get_account_by_id(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def list_profiles(cursor: str | None, limit: int) -> dict:
    profiles = profiles_repo.list_all_profiles()
    offset = _decode_cursor(cursor)
    page = profiles[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(profiles) else None
    return {"items": page, "next_cursor": next_cursor}


def get_profile(profile_id: str) -> Profile:
    profile = profiles_repo.get_profile(profile_id)
    if profile is None:
        raise ProfileNotFoundError(profile_id)
    return profile
