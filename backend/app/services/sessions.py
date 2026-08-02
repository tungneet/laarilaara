"""Session management application services (the authenticated /v1/me/sessions surface)."""
from __future__ import annotations

from app.repositories import sessions as sessions_repo


def list_sessions(account_id: str, current_session_id: str) -> list[dict]:
    items = sessions_repo.list_sessions(account_id)
    return [
        {
            "id": item["id"],
            "created_at": item["createdAt"],
            "expires_at": item["expiresAt"],
            "is_current": item["id"] == current_session_id,
        }
        for item in items
    ]


def revoke_session(account_id: str, session_id: str) -> None:
    sessions_repo.revoke_session(account_id, session_id)
