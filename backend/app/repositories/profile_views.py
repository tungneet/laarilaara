"""Profile view event repository (catalog §7: `POST /v1/discovery/views`
— "Explicitly record a meaningful profile view if not automatic | Idempotent
within dedupe window").

Item shape:  PK = ``PROFILE#{viewerProfileId}``
             SK = ``VIEW#{targetProfileId}#{YYYY-MM-DD}``

The dedupe window is a UTC calendar day: re-recording the same viewer/target
pair on the same day is a no-op that returns the original record.
"""
from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.dynamodb import get_table


def _pk(viewer_profile_id: str) -> str:
    return f"PROFILE#{viewer_profile_id}"


def _sk(target_profile_id: str, day: str) -> str:
    return f"VIEW#{target_profile_id}#{day}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def record_view(viewer_profile_id: str, target_profile_id: str) -> dict:
    now = datetime.now(tz=timezone.utc)
    day = now.date().isoformat()
    table = get_table()
    item = {
        "target_profile_id": target_profile_id,
        "viewed_at": now.isoformat(),
    }
    try:
        table.put_item(
            Item={
                "PK": _pk(viewer_profile_id),
                "SK": _sk(target_profile_id, day),
                "entityType": "ProfileView",
                **item,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            resp = table.get_item(Key={"PK": _pk(viewer_profile_id), "SK": _sk(target_profile_id, day)})
            return _strip(resp["Item"])
        raise
    return item
