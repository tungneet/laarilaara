"""Static seed data for §12 notifications (categories/channels for
`notification-preferences` validation). Not an exhaustive/authoritative
list — small representative set, same convention as
`app/domain/reference_data.py`.
"""
from __future__ import annotations

NOTIFICATION_CATEGORIES = ["match", "message", "interest", "moderation", "system"]
NOTIFICATION_CHANNELS = ["in_app", "email", "push"]
