"""Router for §14 provider webhooks (billing/verification/notifications).

Convention (documented in `app/services/webhooks.py` — no real provider is
wired up yet so there is no provider-mandated request format to match):
JSON body must include an ``id`` field used as the unique external event ID;
headers ``X-Webhook-Timestamp`` (unix seconds) and ``X-Webhook-Signature``
(HMAC-SHA256 hex) authenticate the request in place of a bearer token —
these are public, unauthenticated-by-session endpoints.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Header, Request, status

from app.core.errors import ApiError
from app.schemas.webhook import WebhookAckResponse
from app.services import webhooks as webhooks_service

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

_UNKNOWN_PROVIDER_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND,
    code="WEBHOOK_PROVIDER_NOT_FOUND",
    title="Unknown webhook provider",
)

_INVALID_SIGNATURE_ERROR = ApiError(
    status=status.HTTP_401_UNAUTHORIZED,
    code="WEBHOOK_INVALID_SIGNATURE",
    title="Invalid webhook signature",
)

_REPLAY_REJECTED_ERROR = ApiError(
    status=status.HTTP_401_UNAUTHORIZED,
    code="WEBHOOK_REPLAY_REJECTED",
    title="Webhook timestamp is outside the allowed window",
)

_MALFORMED_BODY_ERROR = ApiError(
    status=status.HTTP_400_BAD_REQUEST,
    code="WEBHOOK_MALFORMED_BODY",
    title="Webhook body must be JSON with an `id` field",
)


async def _handle(
    kind: str,
    provider: str,
    request: Request,
    x_webhook_timestamp: str,
    x_webhook_signature: str,
) -> WebhookAckResponse:
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
        external_id = payload["id"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise _MALFORMED_BODY_ERROR from exc

    try:
        result = webhooks_service.verify_and_capture(
            kind, provider, raw_body, x_webhook_timestamp, x_webhook_signature, external_id, payload
        )
    except webhooks_service.UnknownProviderError as exc:
        raise _UNKNOWN_PROVIDER_ERROR from exc
    except webhooks_service.InvalidSignatureError as exc:
        raise _INVALID_SIGNATURE_ERROR from exc
    except webhooks_service.ReplayRejectedError as exc:
        raise _REPLAY_REJECTED_ERROR from exc
    return WebhookAckResponse(**result)


@router.post("/billing/{provider}", response_model=WebhookAckResponse)
async def billing_webhook(
    provider: str,
    request: Request,
    x_webhook_timestamp: str = Header(...),
    x_webhook_signature: str = Header(...),
) -> WebhookAckResponse:
    return await _handle("billing", provider, request, x_webhook_timestamp, x_webhook_signature)


@router.post("/verification/{provider}", response_model=WebhookAckResponse)
async def verification_webhook(
    provider: str,
    request: Request,
    x_webhook_timestamp: str = Header(...),
    x_webhook_signature: str = Header(...),
) -> WebhookAckResponse:
    return await _handle("verification", provider, request, x_webhook_timestamp, x_webhook_signature)


@router.post("/notifications/{provider}", response_model=WebhookAckResponse)
async def notifications_webhook(
    provider: str,
    request: Request,
    x_webhook_timestamp: str = Header(...),
    x_webhook_signature: str = Header(...),
) -> WebhookAckResponse:
    return await _handle("notifications", provider, request, x_webhook_timestamp, x_webhook_signature)
