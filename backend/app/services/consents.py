"""Consent application services (the authenticated /v1/me/consents surface)."""
from __future__ import annotations

from app.repositories import consents as consents_repo


def record(account_id: str, consent_type: str, granted: bool, policy_version: str) -> dict:
    return consents_repo.record_consent(account_id, consent_type, granted, policy_version)


def summary(account_id: str) -> dict:
    """Return the latest decision per consent type plus the full history."""
    items = sorted(consents_repo.list_consents(account_id), key=lambda item: item["decidedAt"])
    current: dict[str, dict] = {}
    for item in items:
        current[item["consentType"]] = item
    history = list(reversed(items))
    return {"current": current, "history": history}
