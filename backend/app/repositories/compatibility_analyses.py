"""Compatibility analysis repository (catalog §8).

Item shape:  PK = ``ANALYSIS#{id}``   SK = ``ANALYSIS``

GSI1 is used to look up an existing analysis by the unordered
(acting-profile, target-profile) pair, so repeated `POST
/v1/compatibility-analyses` calls for the same pair reuse the same
``analysisId`` (idempotent per catalog note) instead of minting a new one
every time.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(analysis_id: str) -> str:
    return f"ANALYSIS#{analysis_id}"


def _pair_key(profile_a_id: str, profile_b_id: str) -> str:
    a, b = sorted((profile_a_id, profile_b_id))
    return f"COMPATPAIR#{a}#{b}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType", "GSI1PK", "GSI1SK")}


def get_analysis(analysis_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(analysis_id), "SK": "ANALYSIS"})
    item = resp.get("Item")
    return _strip(item) if item else None


def get_by_pair(profile_a_id: str, profile_b_id: str) -> dict | None:
    table = get_table()
    resp = table.query(
        IndexName="GSI1",
        KeyConditionExpression="GSI1PK = :pk",
        ExpressionAttributeValues={":pk": _pair_key(profile_a_id, profile_b_id)},
    )
    items = resp.get("Items", [])
    return _strip(items[0]) if items else None


def upsert_analysis(
    acting_profile_id: str, target_profile_id: str, score: int, factors: dict
) -> dict:
    """Create the analysis for this pair if none exists yet, otherwise
    refresh its score/factors in place and keep the original id/created_at."""
    existing = get_by_pair(acting_profile_id, target_profile_id)
    now = datetime.now(tz=timezone.utc).isoformat()
    analysis_id = existing["id"] if existing else uuid.uuid4().hex
    created_at = existing["created_at"] if existing else now
    item = {
        "id": analysis_id,
        "acting_profile_id": acting_profile_id,
        "target_profile_id": target_profile_id,
        "score": score,
        "factors": factors,
        "created_at": created_at,
        "updated_at": now,
    }
    table = get_table()
    table.put_item(
        Item={
            "PK": _pk(analysis_id),
            "SK": "ANALYSIS",
            "entityType": "CompatibilityAnalysis",
            "GSI1PK": _pair_key(acting_profile_id, target_profile_id),
            "GSI1SK": "ANALYSIS",
            **item,
        }
    )
    return item
