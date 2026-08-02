"""Promo redemption service (catalog §13: `POST /v1/promo-redemptions`)."""
from __future__ import annotations

from app.domain.billing import PROMO_CODES
from app.repositories import promo_redemptions as promo_redemptions_repo


class PromoCodeNotFoundError(Exception):
    pass


def _valid_codes() -> set[str]:
    return {promo["code"] for promo in PROMO_CODES}


def redeem_promo(account_id: str, code: str) -> dict:
    if code not in _valid_codes():
        raise PromoCodeNotFoundError(code)

    existing = promo_redemptions_repo.get_redemption(account_id, code)
    if existing is not None:
        return existing
    return promo_redemptions_repo.put_redemption(account_id, code)
