"""Admin feature-flag repository (catalog §15 "Brands/config": `GET/PATCH
/v1/admin/feature-flags/{key}`).

GET/PATCH only per the baseline catalog — flags must be seeded out of band
(ops tooling / data migration) via `seed_flag`, same convention as
`brand_configs.py`/`experience_configs.py`.

Item shape:  PK = ``FEATUREFLAG#{key}``  SK = ``FEATUREFLAG``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(key: str) -> str:
    return f"FEATUREFLAG#{key}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def seed_flag(key: str, enabled: bool = False) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _pk(key),
        "SK": "FEATUREFLAG",
        "entityType": "FeatureFlag",
        "key": key,
        "enabled": enabled,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_flag(key: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(key), "SK": "FEATUREFLAG"})
    item = resp.get("Item")
    return _strip(item) if item else None


def update_flag(key: str, enabled: bool) -> dict | None:
    existing = get_flag(key)
    if existing is None:
        return None
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(key), "SK": "FEATUREFLAG"},
        UpdateExpression="SET enabled = :enabled, updated_at = :now",
        ExpressionAttributeValues={":enabled": enabled, ":now": now},
    )
    return get_flag(key)
