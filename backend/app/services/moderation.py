"""Moderation-action appeals service (catalog §11:
`POST /v1/moderation-actions/{actionId}/appeals`).

No admin decision surface exists to create `ModerationAction` rows via the
API yet (catalog §15, unbuilt) — `create_action` in
`app.repositories.moderation_actions` exists for tests/future reuse. Appeal
submission is an idempotent per-account upsert (resubmitting overwrites,
same convention as `app.services.ai`'s artifact feedback), and always stays
``status="queued"`` since no appeal-review worker exists either.

Existence-masking: an appeal from an account that is not the action's
affected account gets an identical 404 to a genuinely missing action.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repositories import moderation_actions as moderation_actions_repo

_APPEAL_WINDOW_DAYS = 14


class ModerationActionNotFoundError(Exception):
    pass


class ModerationAppealWindowExpiredError(Exception):
    pass


def create_appeal(account_id: str, action_id: str, reason: str) -> dict:
    action = moderation_actions_repo.get_action(action_id)
    if action is None or action["affected_account_id"] != account_id:
        raise ModerationActionNotFoundError(action_id)
    created_at = datetime.fromisoformat(action["created_at"])
    if datetime.now(tz=timezone.utc) - created_at > timedelta(days=_APPEAL_WINDOW_DAYS):
        raise ModerationAppealWindowExpiredError(action_id)
    return moderation_actions_repo.put_appeal(action_id, account_id, reason)
