"""Admin experience-config repository (catalog §15 "Brands/config":
`GET/PATCH /v1/admin/experiences/{id}`).

Mirrors `brand_configs.py` exactly (same GET/PATCH-only, seed-out-of-band
shape) for the sibling "experience" concept referenced by
`app/services/profile_brands.py`'s per-profile experience values.

Item shape:  PK = ``EXPERIENCECONFIG#{id}``  SK = ``EXPERIENCECONFIG``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(experience_id: str) -> str:
    return f"EXPERIENCECONFIG#{experience_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def seed_experience(experience_id: str, name: str, active: bool = True) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _pk(experience_id),
        "SK": "EXPERIENCECONFIG",
        "entityType": "ExperienceConfig",
        "id": experience_id,
        "name": name,
        "active": active,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_experience(experience_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(experience_id), "SK": "EXPERIENCECONFIG"})
    item = resp.get("Item")
    return _strip(item) if item else None


def update_experience(experience_id: str, name: str | None, active: bool | None) -> dict | None:
    existing = get_experience(experience_id)
    if existing is None:
        return None
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    new_name = name if name is not None else existing["name"]
    new_active = active if active is not None else existing["active"]
    table.update_item(
        Key={"PK": _pk(experience_id), "SK": "EXPERIENCECONFIG"},
        UpdateExpression="SET #name = :name, active = :active, updated_at = :now",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={":name": new_name, ":active": new_active, ":now": now},
    )
    return get_experience(experience_id)
