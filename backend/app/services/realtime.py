"""Realtime WebSocket service (catalog §9 WebSocket half):
`POST /v1/realtime-tokens`, `$connect`/`$disconnect`/`$default` routes, and
server->client push for `message.created`, `message.updated`,
`message.deleted`, `conversation.read`, and `typing.changed`.

`operation.updated`, `notification.created`, and `match.updated` are NOT
wired up yet — no code path in this codebase currently constructs those
events (operations/notifications/matches were all built before this
realtime layer existed); documented gap, same class as other "no worker
reads this yet" notes elsewhere in this codebase.

Locally (uvicorn/pytest) `$connect`/`$disconnect`/`$default` are a native
FastAPI `@router.websocket(...)` route (see `app/routers/realtime.py`) and
push goes through the in-process `app.core.realtime_manager.manager`. On
AWS, `$connect`/`$disconnect`/`$default` are three separate Lambda
integrations on an API Gateway WebSocket API (NOT reachable through the
Mangum ASGI adapter used for the REST API), and push goes through the
`apigatewaymanagementapi` `PostToConnection` call using the connection row's
stored `api_gateway_endpoint`. `push_event` is the seam where that swap
happens; everything above it (token issuance, connection bookkeeping, event
construction) is deployment-shape-agnostic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.realtime_manager import manager
from app.core.security import InvalidTokenError, create_realtime_token, decode_realtime_token
from app.repositories import conversations as conversations_repo
from app.repositories import realtime_connections as connections_repo
from app.services import profiles as profiles_service

_SERVER_EVENT_TYPES = {
    "message.created",
    "message.updated",
    "message.deleted",
    "conversation.read",
    "typing.changed",
}
_CLIENT_ACTIONS = {"typing.start", "typing.stop"}


class RealtimeTokenInvalidError(Exception):
    pass


def issue_token(account_id: str, acting_profile_id: str) -> tuple[str, int]:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)
    return create_realtime_token(account_id, acting_profile_id)


def resolve_connect_token(token: str) -> tuple[str, str]:
    """Validate a `$connect` query-param token. Returns (account_id, profile_id)."""
    try:
        payload = decode_realtime_token(token)
    except InvalidTokenError as exc:
        raise RealtimeTokenInvalidError(str(exc)) from exc
    return payload["sub"], payload["pid"]


def register_connection(account_id: str, profile_id: str) -> str:
    connection_id = uuid.uuid4().hex
    connections_repo.create_connection(connection_id, account_id, profile_id)
    return connection_id


def unregister_connection(profile_id: str, connection_id: str) -> None:
    manager.disconnect(connection_id)
    connections_repo.delete_connection(profile_id, connection_id)


def _make_event(event_type: str, resource_id: str, payload: dict) -> dict:
    return {
        "eventId": uuid.uuid4().hex,
        "type": event_type,
        "occurredAt": datetime.now(tz=timezone.utc).isoformat(),
        "resourceId": resource_id,
        "payload": payload,
    }


async def push_to_profile(profile_id: str, event: dict) -> None:
    """Fan out `event` to every live connection for `profile_id`. A dead
    connection (analogous to AWS `GoneException`/410) is deleted, mirroring
    the catalog's documented cleanup behavior.
    """
    for connection in connections_repo.list_connections_for_profile(profile_id):
        connection_id = connection["connection_id"]
        delivered = await manager.send(connection_id, event)
        if not delivered:
            connections_repo.delete_connection(profile_id, connection_id)


async def notify_conversation(
    conversation_id: str, event_type: str, exclude_profile_id: str | None, payload: dict
) -> None:
    """Push `event_type` to every conversation participant except
    `exclude_profile_id` (typically the actor who triggered it).
    """
    conversation = conversations_repo.get_conversation(conversation_id)
    if conversation is None:
        return
    event = _make_event(event_type, conversation_id, payload)
    for profile_id in (conversation["profile_a_id"], conversation["profile_b_id"]):
        if profile_id == exclude_profile_id:
            continue
        await push_to_profile(profile_id, event)


async def handle_client_action(
    conversation_id: str, acting_profile_id: str, action: str
) -> None:
    """`$default` route: the only client-originated events are typing
    start/stop hints (catalog §9). Anything else is silently ignored —
    durable writes always go through REST, never this route.
    """
    if action not in _CLIENT_ACTIONS:
        return
    typing = action == "typing.start"
    await notify_conversation(
        conversation_id,
        "typing.changed",
        exclude_profile_id=acting_profile_id,
        payload={"profileId": acting_profile_id, "typing": typing},
    )
