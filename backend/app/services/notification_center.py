"""In-app notification center service (catalog §12: notifications,
notification-preferences, push-endpoints). All resources here are
account-scoped (like `app.services.sessions`/`app.services.consents`), not
profile-scoped — an in-app inbox belongs to the logged-in account, not to a
specific matchmaking profile it manages.

KNOWN GAP (shared with `app.services.reports`/`app.services.moderation`):
no SQS-triggered notification worker exists anywhere in this codebase yet,
so nothing in the running API ever calls `create_notification` — it exists
for tests/future worker reuse. Push-endpoint registration is a real,
immediately-usable resource (register/revoke), but nothing yet sends to it
(actual delivery is deferred to that same future worker).
"""
from __future__ import annotations

from datetime import datetime

from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.domain.notifications import NOTIFICATION_CATEGORIES, NOTIFICATION_CHANNELS
from app.repositories import notification_center as notifications_repo
from app.repositories import notification_preferences as preferences_repo
from app.repositories import push_endpoints as push_endpoints_repo


class NotificationNotFoundError(Exception):
    pass


class InvalidPreferenceValueError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class PushEndpointNotFoundError(Exception):
    pass


def list_notifications(account_id: str, cursor: str | None, limit: int) -> dict:
    items = notifications_repo.list_notifications(account_id)
    offset = _decode_cursor(cursor)
    page = items[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(items) else None
    return {"items": page, "next_cursor": next_cursor}


def mark_read(account_id: str, notification_id: str) -> dict:
    notification = notifications_repo.get_notification_by_id(notification_id)
    if notification is None or notification["account_id"] != account_id:
        raise NotificationNotFoundError(notification_id)
    if notification["read_at"] is None:
        sort_key = _sort_key_from_created_at(notification["created_at"])
        notifications_repo.mark_read(account_id, sort_key, notification["id"])
        notification = notifications_repo.get_notification_by_id(notification_id)
    return notification


def mark_all_read(account_id: str, through: str | None) -> int:
    marked = 0
    for notification in notifications_repo.list_notifications(account_id):
        if notification["read_at"] is not None:
            continue
        if through is not None and notification["created_at"] > through:
            continue
        sort_key = _sort_key_from_created_at(notification["created_at"])
        notifications_repo.mark_read(account_id, sort_key, notification["id"])
        marked += 1
    return marked


def _sort_key_from_created_at(created_at: str) -> str:
    return datetime.fromisoformat(created_at).strftime("%Y%m%dT%H%M%S%f")


def get_preferences(account_id: str) -> dict:
    stored = preferences_repo.get_preferences(account_id)
    if stored is None:
        # Default: every known category enabled on every known channel.
        return {"categories": {c: list(NOTIFICATION_CHANNELS) for c in NOTIFICATION_CATEGORIES}}
    return stored


def put_preferences(account_id: str, categories: dict[str, list[str]]) -> dict:
    for category, channels in categories.items():
        if category not in NOTIFICATION_CATEGORIES:
            raise InvalidPreferenceValueError(f"unknown category: {category}")
        for channel in channels:
            if channel not in NOTIFICATION_CHANNELS:
                raise InvalidPreferenceValueError(f"unknown channel: {channel}")
    return preferences_repo.put_preferences(account_id, categories)


def create_push_endpoint(account_id: str, platform: str, token: str) -> dict:
    return push_endpoints_repo.create_endpoint(account_id, platform, token)


def revoke_push_endpoint(account_id: str, endpoint_id: str) -> None:
    endpoint = push_endpoints_repo.get_endpoint_by_id(endpoint_id)
    if endpoint is None or endpoint["account_id"] != account_id:
        raise PushEndpointNotFoundError(endpoint_id)
    push_endpoints_repo.delete_endpoint(account_id, endpoint_id)
