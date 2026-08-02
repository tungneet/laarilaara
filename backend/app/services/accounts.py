"""Account profile application services (the authenticated /v1/me surface)."""
from __future__ import annotations

from app.domain.accounts import Account
from app.repositories import accounts as accounts_repo


class AccountNotFoundError(Exception):
    pass


def get_profile(account_id: str) -> Account:
    account = accounts_repo.get_account_by_id(account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def update_profile(account_id: str, locale: str | None) -> Account:
    if locale is not None:
        accounts_repo.update_locale(account_id, locale)
    return get_profile(account_id)
