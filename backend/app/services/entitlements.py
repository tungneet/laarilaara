"""Entitlements seam.

Single chokepoint for every action that could ever be gated by the
freemium/premium model. Today it grants everything (free tier is unlimited), so
building endpoints against it costs nothing now, but switching a plan later is a
data/config change here — never scattered ``if is_premium`` checks in endpoints.

When payments land, ``check`` will look up per-tier limits (from config/data)
and current usage, and raise ``ApiError(403, "ENTITLEMENT_REQUIRED", ...)`` when
a limit is exceeded.
"""
from __future__ import annotations

from enum import Enum

from app.domain.accounts import Account


class Action(str, Enum):
    """Gatable actions. Extend as premium-limited features are added."""

    SEND_INTEREST = "send_interest"
    START_CONVERSATION = "start_conversation"
    RUN_AI_DRAFT = "run_ai_draft"
    ADVANCED_SEARCH = "advanced_search"
    SEE_WHO_VIEWED_ME = "see_who_viewed_me"


class Decision:
    def __init__(self, allowed: bool, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason


def check(account: Account, action: Action) -> Decision:
    """Return an allow/deny decision for an action.

    Currently allows everything. Do not inline plan logic elsewhere; extend this
    function (and its config-driven limits) instead.
    """
    return Decision(allowed=True)


def effective_view(account: Account) -> list[dict]:
    """Catalog §13 `GET /v1/entitlements`: the effective capability view for
    every gatable action, using the same `check` seam so this never drifts
    from the actual enforcement decisions.
    """
    view = []
    for action in Action:
        decision = check(account, action)
        view.append({"action": action.value, "allowed": decision.allowed, "reason": decision.reason})
    return view
