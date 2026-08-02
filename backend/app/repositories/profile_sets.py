"""Generic replace-set profile section repository (catalog §5 — "Sections"
batch B: communities, religious-practices, languages, interests — all
"GET current set / PUT full replacement" resources with the same shape).

Item shape:  PK = ``PROFILE#{profileId}``   SK = ``SET#{SET_NAME}``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _set_sk(name: str) -> str:
    return f"SET#{name}"


def get_set(profile_id: str, name: str) -> dict:
    """Return ``{"values": [...], "updated_at": ...}``, defaulting to an
    empty list if the set has never been written.
    """
    table = get_table()
    resp = table.get_item(Key={"PK": _profile_pk(profile_id), "SK": _set_sk(name)})
    item = resp.get("Item")
    if item is None:
        return {"values": [], "updated_at": None}
    return {"values": list(item.get("values", [])), "updated_at": item.get("updated_at")}


def replace_set(profile_id: str, name: str, values: list[str]) -> dict:
    """Fully replace the stored set with ``values`` (deduplicated, order
    preserved) and persist.
    """
    deduped = list(dict.fromkeys(values))
    now = datetime.now(tz=timezone.utc).isoformat()
    table = get_table()
    table.put_item(
        Item={
            "PK": _profile_pk(profile_id),
            "SK": _set_sk(name),
            "entityType": "ProfileSet",
            "values": deduped,
            "updated_at": now,
        }
    )
    return {"values": deduped, "updated_at": now}
