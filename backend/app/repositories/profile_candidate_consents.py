"""Candidate-consent repository (DynamoDB single-table).

Append-only, mirrors ``app/repositories/consents.py`` but scoped to a
profile rather than an account: a verified candidate's decision to authorize
publication/management of their own profile (catalog §5).

Item:  PK = ``PROFILE#{profileId}``   SK = ``CANDIDATECONSENT#{isoTimestamp}``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def record_candidate_consent(
    profile_id: str, decided_by_account_id: str, decision: str, granted: bool
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    item = {
        "PK": _profile_pk(profile_id),
        "SK": f"CANDIDATECONSENT#{now.isoformat()}",
        "entityType": "ProfileCandidateConsent",
        "profileId": profile_id,
        "decidedByAccountId": decided_by_account_id,
        "decision": decision,
        "granted": granted,
        "decidedAt": now.isoformat(),
    }
    table.put_item(Item=item)
    return item
