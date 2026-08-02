"""Conversations and messages service (catalog §9: `GET /v1/conversations`,
`GET /v1/conversations/{conversationId}`, `GET/POST /v1/conversations/{id}/messages`,
`PATCH/DELETE /v1/conversations/{id}/messages/{messageId}`,
`POST /v1/conversations/{id}/read`, `POST /v1/conversations/{id}/mute`).

Conversations are 1:1 with matches — created automatically when an interest
is accepted (see `app.services.interests.accept_interest`), never via a
dedicated create endpoint (none exists in the catalog).

KNOWN GAPS (documented, no existing infra to build on):
- Content moderation on send now exists (catalog's "fast safety policy") —
  message bodies are run through the central `app.core.ai_engine`'s
  `enforce_moderation` (Block 14) before a message is created, and blocked
  synchronously (`MessageContentBlockedError`) above the configured
  threshold. This does NOT yet cover message edits (`edit_message` still has
  no moderation check) — flagged as a follow-up, same class of gap.
- Edit window is a simple fixed 15-minute constant, not a configurable
  policy; `If-Match`/optimistic-concurrency headers are not implemented —
  `revision` is tracked but not enforced against a client-supplied value.
- Delete is sender-only; the catalog also allows an "admin policy" deletion
  path, but no admin role exists anywhere in this codebase yet.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core import ai_engine
from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.repositories import conversations as conversations_repo
from app.repositories import media_assets as media_assets_repo
from app.repositories import messages as messages_repo
from app.services import profiles as profiles_service
from app.services import realtime as realtime_service

_EDIT_WINDOW_MINUTES = 15


class ConversationNotFoundError(Exception):
    pass


class MessageNotFoundError(Exception):
    pass


class MessageEditWindowExpiredError(Exception):
    pass


class MessageEmptyError(Exception):
    pass


class MediaAssetNotFoundError(Exception):
    pass


class MessageContentBlockedError(Exception):
    """Raised when `app.core.ai_engine.enforce_moderation` flags a message
    body at/above the configured block threshold."""

    def __init__(self, moderation: ai_engine.ModerationResult) -> None:
        super().__init__("message content blocked by moderation")
        self.moderation = moderation


def _get_conversation_or_404(conversation_id: str) -> dict:
    conversation = conversations_repo.get_conversation(conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    return conversation


def _require_participant(acting_profile_id: str, conversation: dict) -> None:
    if acting_profile_id not in (conversation["profile_a_id"], conversation["profile_b_id"]):
        # Mask existence: a non-participant sees the same 404 as a missing conversation.
        raise ConversationNotFoundError(conversation["id"])


def get_conversation_for_participant(acting_profile_id: str, conversation_id: str) -> dict:
    """Public helper reused by `app.services.ai` (§10 conversation-scoped AI
    endpoints) so it doesn't duplicate the existence-masking participant check.
    """
    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)
    return conversation


def _get_message_or_404(conversation_id: str, message_id: str) -> dict:
    message = messages_repo.get_message_by_id(message_id)
    if message is None or message["conversation_id"] != conversation_id:
        raise MessageNotFoundError(message_id)
    return message


def _unread_count(conversation: dict, acting_profile_id: str) -> int:
    marker = conversation.get("read_markers", {}).get(acting_profile_id)
    messages = messages_repo.list_messages(conversation["id"])
    count = 0
    for message in messages:
        if message["sender_profile_id"] == acting_profile_id:
            continue
        if message["status"] == "deleted":
            continue
        if marker is None or message["sort_key"] > marker:
            count += 1
    return count


def _to_response(conversation: dict, acting_profile_id: str) -> dict:
    return {
        **conversation,
        "unread_count": _unread_count(conversation, acting_profile_id),
        "muted": conversation.get("muted", {}).get(acting_profile_id, False),
    }


def list_conversations(
    account_id: str, acting_profile_id: str, cursor: str | None, limit: int
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    items = [
        _to_response(conversation, acting_profile_id)
        for conversation in conversations_repo.list_for_profile(acting_profile_id)
    ]
    offset = _decode_cursor(cursor)
    page = items[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(items) else None
    return {"items": page, "next_cursor": next_cursor}


def get_conversation(account_id: str, acting_profile_id: str, conversation_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)
    return _to_response(conversation, acting_profile_id)


def list_messages(
    account_id: str, acting_profile_id: str, conversation_id: str, cursor: str | None, limit: int
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)

    items = messages_repo.list_messages(conversation_id)
    offset = _decode_cursor(cursor)
    page = items[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(items) else None
    return {"items": page, "next_cursor": next_cursor}


async def send_message(
    account_id: str,
    acting_profile_id: str,
    conversation_id: str,
    client_message_id: str,
    body: str | None,
    attachment_asset_id: str | None,
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)

    if not body and not attachment_asset_id:
        raise MessageEmptyError()
    if attachment_asset_id is not None and media_assets_repo.get_asset(attachment_asset_id) is None:
        raise MediaAssetNotFoundError(attachment_asset_id)
    try:
        ai_engine.enforce_moderation(body)
    except ai_engine.ContentBlockedError as exc:
        raise MessageContentBlockedError(exc.moderation) from exc

    existing = messages_repo.find_by_client_message_id(
        conversation_id, acting_profile_id, client_message_id
    )
    if existing is not None:
        return existing

    message = messages_repo.create_message(
        conversation_id, acting_profile_id, client_message_id, body, attachment_asset_id
    )
    preview = (body or "[attachment]")[:120]
    conversations_repo.update_last_message(conversation_id, preview, message["created_at"])
    await realtime_service.notify_conversation(
        conversation_id, "message.created", exclude_profile_id=acting_profile_id, payload=message
    )
    return message


async def edit_message(
    account_id: str, acting_profile_id: str, conversation_id: str, message_id: str, body: str
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)

    message = _get_message_or_404(conversation_id, message_id)
    if message["sender_profile_id"] != acting_profile_id or message["status"] == "deleted":
        raise MessageNotFoundError(message_id)

    created_at = datetime.fromisoformat(message["created_at"])
    if datetime.now(tz=timezone.utc) - created_at > timedelta(minutes=_EDIT_WINDOW_MINUTES):
        raise MessageEditWindowExpiredError(message_id)

    updated = messages_repo.update_body(conversation_id, message_id, message["sort_key"], body)
    await realtime_service.notify_conversation(
        conversation_id, "message.updated", exclude_profile_id=acting_profile_id, payload=updated
    )
    return updated


async def delete_message(
    account_id: str, acting_profile_id: str, conversation_id: str, message_id: str
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)

    message = _get_message_or_404(conversation_id, message_id)
    if message["sender_profile_id"] != acting_profile_id:
        raise MessageNotFoundError(message_id)
    if message["status"] == "deleted":
        return message

    deleted = messages_repo.soft_delete(conversation_id, message_id, message["sort_key"])
    await realtime_service.notify_conversation(
        conversation_id, "message.deleted", exclude_profile_id=acting_profile_id, payload=deleted
    )
    return deleted


async def mark_read(
    account_id: str, acting_profile_id: str, conversation_id: str, message_id: str
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)

    message = _get_message_or_404(conversation_id, message_id)
    current_marker = conversation.get("read_markers", {}).get(acting_profile_id)
    if current_marker is not None and current_marker >= message["sort_key"]:
        # Monotonic: never move the marker backwards.
        return _to_response(conversation, acting_profile_id)

    updated = conversations_repo.set_read_marker(conversation_id, acting_profile_id, message["sort_key"])
    await realtime_service.notify_conversation(
        conversation_id,
        "conversation.read",
        exclude_profile_id=acting_profile_id,
        payload={"profileId": acting_profile_id, "messageId": message["id"]},
    )
    return _to_response(updated, acting_profile_id)


def set_mute(
    account_id: str, acting_profile_id: str, conversation_id: str, muted: bool
) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.edit")
    profiles_service.get_or_404(acting_profile_id)

    conversation = _get_conversation_or_404(conversation_id)
    _require_participant(acting_profile_id, conversation)

    updated = conversations_repo.set_muted(conversation_id, acting_profile_id, muted)
    return _to_response(updated, acting_profile_id)
