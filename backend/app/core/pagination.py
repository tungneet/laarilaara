"""Shared base64-offset cursor pagination helper.

Simplified pagination convention used across §7 discovery and §8
interests/matches: the cursor is just a base64-encoded integer offset into
an in-memory (already fetched/sorted) list, not a real keyset or
ranking-version-encoded cursor. Documented simplification pending real
search/list infrastructure.
"""
from __future__ import annotations

import base64


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(base64.urlsafe_b64decode(cursor.encode()).decode()))
    except (ValueError, UnicodeDecodeError):
        return 0
