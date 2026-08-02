"""Static seed data for §13 billing (approved promo codes for
`POST /v1/promo-redemptions`). Not an exhaustive/authoritative list — same
convention as `VERIFICATION_CHECKS`/`PLANS` in `app/domain/reference_data.py`.
"""
from __future__ import annotations

PROMO_CODES = [
    {"code": "WELCOME10", "description": "10% off first payment", "discount_percent": 10},
    {"code": "LAARA25", "description": "25% off first payment", "discount_percent": 25},
]
