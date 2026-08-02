"""Profile repository (DynamoDB single-table).

Profile item:  PK = ``PROFILE#{id}``   SK = ``PROFILE``

Root fields only (personal-details/narratives/lifestyle/etc. sections are
separate items added in later batches, per catalog §5 "Sections").
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr

from app.core.dynamodb import get_table
from app.domain.profiles import Profile, ProfileRelationship, ProfileStatus


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _to_item(profile: Profile) -> dict:
    return {
        "PK": _profile_pk(profile.id),
        "SK": "PROFILE",
        "entityType": "Profile",
        "id": profile.id,
        "ownerAccountId": profile.owner_account_id,
        "relationship": profile.relationship.value,
        "status": profile.status.value,
        "version": profile.version,
        "locale": profile.locale,
        "createdAt": profile.created_at.isoformat(),
        "updatedAt": profile.updated_at.isoformat(),
        "submittedAt": profile.submitted_at.isoformat() if profile.submitted_at else None,
        "publishedAt": profile.published_at.isoformat() if profile.published_at else None,
        "pausedAt": profile.paused_at.isoformat() if profile.paused_at else None,
    }


def _from_item(item: dict) -> Profile:
    return Profile(
        id=item["id"],
        owner_account_id=item["ownerAccountId"],
        relationship=ProfileRelationship(item["relationship"]),
        status=ProfileStatus(item["status"]),
        version=item["version"],
        locale=item.get("locale", "en"),
        created_at=item["createdAt"],
        updated_at=item["updatedAt"],
        submitted_at=item.get("submittedAt"),
        published_at=item.get("publishedAt"),
        paused_at=item.get("pausedAt"),
    )


def create_profile(
    owner_account_id: str, relationship: ProfileRelationship, locale: str = "en"
) -> Profile:
    profile = Profile(
        id=uuid.uuid4().hex,
        owner_account_id=owner_account_id,
        relationship=relationship,
        locale=locale,
    )
    table = get_table()
    table.put_item(Item=_to_item(profile))
    return profile


def get_profile(profile_id: str) -> Profile | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _profile_pk(profile_id), "SK": "PROFILE"})
    item = resp.get("Item")
    return _from_item(item) if item else None


def list_published_profiles() -> list[Profile]:
    """Return all PUBLISHED profiles via a table scan.

    KNOWN SIMPLIFICATION (catalog §7 discovery): there is no real search
    index (OpenSearch/etc.) in this codebase yet, so discovery search and
    recommendations both scan every profile and filter in Python. Fine at
    dev/test scale; must be replaced by a real index before production scale.
    """
    table = get_table()
    items: list[dict] = []
    scan_kwargs: dict = {
        "FilterExpression": Attr("entityType").eq("Profile") & Attr("status").eq(
            ProfileStatus.PUBLISHED.value
        )
    }
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return [_from_item(item) for item in items]


def list_all_profiles() -> list[Profile]:
    """Admin-only directory listing (catalog §15), any status. Table scan —
    same documented "dev/test scale" tradeoff as `list_published_profiles`.
    """
    table = get_table()
    items: list[dict] = []
    scan_kwargs: dict = {"FilterExpression": Attr("entityType").eq("Profile")}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key
    return [_from_item(item) for item in items]


def update_locale(profile_id: str, locale: str) -> Profile:
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    resp = table.update_item(
        Key={"PK": _profile_pk(profile_id), "SK": "PROFILE"},
        UpdateExpression="SET locale = :locale, updatedAt = :now, version = version + :one",
        ExpressionAttributeValues={":locale": locale, ":now": now.isoformat(), ":one": 1},
        ReturnValues="ALL_NEW",
    )
    return _from_item(resp["Attributes"])


def touch_version(profile_id: str) -> None:
    """Bump the profile aggregate's ``version`` and ``updatedAt`` without
    changing any other field. Called by section writes (personal-details,
    narratives, lifestyle, visibility, etc.) that affect compatibility or
    discovery input, per catalog §5 "Sections".
    """
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    table.update_item(
        Key={"PK": _profile_pk(profile_id), "SK": "PROFILE"},
        UpdateExpression="SET updatedAt = :now, version = version + :one",
        ExpressionAttributeValues={":now": now.isoformat(), ":one": 1},
    )


def set_status(
    profile_id: str,
    status: ProfileStatus,
    *,
    timestamp_field: str | None = None,
) -> Profile:
    """Transition status, bump version, and stamp updatedAt (and optionally
    one lifecycle timestamp such as ``submittedAt``/``publishedAt``/``pausedAt``).
    """
    table = get_table()
    now = datetime.now(tz=timezone.utc)
    update_expr = "SET #status = :status, updatedAt = :now, version = version + :one"
    names = {"#status": "status"}
    values: dict = {":status": status.value, ":now": now.isoformat(), ":one": 1}
    if timestamp_field is not None:
        update_expr += f", {timestamp_field} = :now"

    resp = table.update_item(
        Key={"PK": _profile_pk(profile_id), "SK": "PROFILE"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return _from_item(resp["Attributes"])
