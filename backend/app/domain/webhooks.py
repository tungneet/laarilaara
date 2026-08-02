"""Static seed data for §14 provider webhooks (per-kind provider allowlist).
Representative fake provider names, not a real integration — no live
billing/verification/notification provider is wired up yet.
"""
from __future__ import annotations

ALLOWED_PROVIDERS = {
    "billing": ["stripe"],
    "verification": ["persona", "onfido"],
    "notifications": ["ses", "sns"],
}
