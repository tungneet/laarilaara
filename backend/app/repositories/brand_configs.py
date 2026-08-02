"""Admin brand-config repository (catalog §15 "Brands/config": `GET/PATCH
/v1/admin/brands/{id}`).

Distinct from `app/services/profile_brands.py` (catalog §5), which stores a
per-*profile* free-text brand/experience value with format-only validation.
This module is the authoritative, admin-managed catalog of brand ids those
per-profile values are meant to be checked against eventually (documented
gap in `profile_brands.py`: "no seeded controlled-option list ... yet").

Baseline catalog only exposes GET/PATCH (no create/delete) — brand configs
must be seeded out of band (ops tooling / data migration); this repo's
`seed_brand` exists for that and for white-box test setup.

Item shape:  PK = ``BRANDCONFIG#{id}``  SK = ``BRANDCONFIG``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(brand_id: str) -> str:
    return f"BRANDCONFIG#{brand_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def seed_brand(brand_id: str, name: str, active: bool = True) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _pk(brand_id),
        "SK": "BRANDCONFIG",
        "entityType": "BrandConfig",
        "id": brand_id,
        "name": name,
        "active": active,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_brand(brand_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(brand_id), "SK": "BRANDCONFIG"})
    item = resp.get("Item")
    return _strip(item) if item else None


def update_brand(brand_id: str, name: str | None, active: bool | None) -> dict | None:
    existing = get_brand(brand_id)
    if existing is None:
        return None
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    new_name = name if name is not None else existing["name"]
    new_active = active if active is not None else existing["active"]
    table.update_item(
        Key={"PK": _pk(brand_id), "SK": "BRANDCONFIG"},
        UpdateExpression="SET #name = :name, active = :active, updated_at = :now",
        ExpressionAttributeNames={"#name": "name"},
        ExpressionAttributeValues={":name": new_name, ":active": new_active, ":now": now},
    )
    return get_brand(brand_id)
