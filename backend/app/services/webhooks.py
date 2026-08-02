"""Provider webhook service (catalog §14): signature verification, replay
rejection, and durable capture for billing/verification/notifications
webhooks.

Every webhook Lambda invocation here does ONLY signature verification and
durable capture (a single conditional DynamoDB write), matching the
catalog's guidance to keep the response fast and defer further processing —
except there IS no further-processing worker in this codebase yet (same
class of gap as reports/notifications/billing), so captured events just sit
durably recorded and unread until such a worker exists.

Signing scheme (our own convention — no real provider is wired up yet, so
there is no provider-mandated format to match): HMAC-SHA256 over
``f"{timestamp}.{raw_body}"`` using a single shared secret
(`settings.webhook_signing_secret`), hex-compared with `hmac.compare_digest`.
A production integration would swap this for each real provider's actual
signature scheme (e.g. Stripe's `Stripe-Signature` header format) without
changing the durable-capture/idempotency logic below.
"""
from __future__ import annotations

import hashlib
import hmac
import time

from app.core.config import get_settings
from app.domain.webhooks import ALLOWED_PROVIDERS
from app.repositories import webhook_events as webhook_events_repo

_MAX_TIMESTAMP_SKEW_SECONDS = 5 * 60


class UnknownProviderError(Exception):
    pass


class InvalidSignatureError(Exception):
    pass


class ReplayRejectedError(Exception):
    pass


def _verify_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    secret = get_settings().webhook_signing_secret.encode("utf-8")
    signed_payload = timestamp.encode("utf-8") + b"." + raw_body
    expected = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_and_capture(
    kind: str,
    provider: str,
    raw_body: bytes,
    timestamp: str,
    signature: str,
    external_id: str,
    payload: dict,
) -> dict:
    if provider not in ALLOWED_PROVIDERS.get(kind, []):
        raise UnknownProviderError(provider)

    if not _verify_signature(raw_body, timestamp, signature):
        raise InvalidSignatureError

    try:
        event_time = float(timestamp)
    except ValueError as exc:
        raise InvalidSignatureError from exc
    if abs(time.time() - event_time) > _MAX_TIMESTAMP_SKEW_SECONDS:
        raise ReplayRejectedError

    _, created = webhook_events_repo.capture_event(kind, provider, external_id, payload)
    return {"received": True, "duplicate": not created}
