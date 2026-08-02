"""Tests for catalog §14 "Provider webhooks" (3 HTTP operations).

These are unauthenticated-by-session endpoints — signature verification
(HMAC-SHA256 over `f"{timestamp}.{raw_body}"` with the shared
`settings.webhook_signing_secret`) replaces the usual bearer token. No real
provider is wired up (see `app/services/webhooks.py` module docstring), so
tests sign requests themselves using the same local dev secret the app uses.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app
from app.repositories import webhook_events as webhook_events_repo

client = TestClient(app)


def _sign(raw_body: bytes, timestamp: str) -> str:
    secret = get_settings().webhook_signing_secret.encode("utf-8")
    signed_payload = timestamp.encode("utf-8") + b"." + raw_body
    return hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()


def _post_webhook(path: str, body: dict, timestamp: str | None = None, signature: str | None = None):
    raw_body = json.dumps(body).encode("utf-8")
    ts = timestamp if timestamp is not None else str(time.time())
    sig = signature if signature is not None else _sign(raw_body, ts)
    return client.post(
        path,
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": ts,
            "X-Webhook-Signature": sig,
        },
    )


def test_billing_webhook_captures_and_is_idempotent(dynamo_table):
    body = {"id": "evt_billing_1", "type": "payment_succeeded"}

    resp1 = _post_webhook("/v1/webhooks/billing/stripe", body)
    assert resp1.status_code == 200
    assert resp1.json() == {"received": True, "duplicate": False}

    resp2 = _post_webhook("/v1/webhooks/billing/stripe", body)
    assert resp2.status_code == 200
    assert resp2.json() == {"received": True, "duplicate": True}

    stored = webhook_events_repo.get_event("billing", "stripe", "evt_billing_1")
    assert stored is not None
    assert stored["payload"]["type"] == "payment_succeeded"


def test_verification_webhook_unknown_provider_is_404(dynamo_table):
    resp = _post_webhook("/v1/webhooks/verification/not-a-real-provider", {"id": "evt_1"})
    assert resp.status_code == 404


def test_notifications_webhook_invalid_signature_is_401(dynamo_table):
    resp = _post_webhook(
        "/v1/webhooks/notifications/ses", {"id": "evt_1"}, signature="deadbeef" * 8
    )
    assert resp.status_code == 401


def test_billing_webhook_stale_timestamp_is_401(dynamo_table):
    stale_ts = str(time.time() - 3600)
    body = {"id": "evt_billing_stale"}
    resp = _post_webhook("/v1/webhooks/billing/stripe", body, timestamp=stale_ts)
    assert resp.status_code == 401


def test_billing_webhook_malformed_body_is_400(dynamo_table):
    resp = client.post(
        "/v1/webhooks/billing/stripe",
        content=b"not json",
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Timestamp": str(time.time()),
            "X-Webhook-Signature": "irrelevant",
        },
    )
    assert resp.status_code == 400


def test_verification_webhook_happy_path(dynamo_table):
    resp = _post_webhook("/v1/webhooks/verification/persona", {"id": "evt_verif_1", "result": "pass"})
    assert resp.status_code == 200
    assert resp.json()["duplicate"] is False
