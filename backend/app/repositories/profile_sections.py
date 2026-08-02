"""Generic single-resource profile section repository (catalog §5 — "Sections").

Covers the "one current resource per single-valued section" sections:
personal-details, narratives, lifestyle, visibility (this batch). Each
section is stored as its own item so it can be read/written independently of
the profile aggregate and of other sections.

Item shape:  PK = ``PROFILE#{profileId}``   SK = ``SECTION#{SECTION_NAME}``
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _profile_pk(profile_id: str) -> str:
    return f"PROFILE#{profile_id}"


def _section_sk(section: str) -> str:
    return f"SECTION#{section}"


def get_section(profile_id: str, section: str) -> dict:
    """Return the section's stored fields (without PK/SK/entityType), or an
    empty dict if the section has never been written.
    """
    table = get_table()
    resp = table.get_item(Key={"PK": _profile_pk(profile_id), "SK": _section_sk(section)})
    item = resp.get("Item")
    if item is None:
        return {}
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def patch_section(profile_id: str, section: str, updates: dict) -> dict:
    """Merge ``updates`` (only keys with non-``None`` values) into the
    section's stored fields and persist. Returns the merged fields.
    """
    existing = get_section(profile_id, section)
    merged = {**existing, **{k: v for k, v in updates.items() if v is not None}}
    now = datetime.now(tz=timezone.utc).isoformat()
    merged["updated_at"] = now

    table = get_table()
    table.put_item(
        Item={
            "PK": _profile_pk(profile_id),
            "SK": _section_sk(section),
            "entityType": "ProfileSection",
            **merged,
        }
    )
    return merged


def replace_section(profile_id: str, section: str, fields: dict) -> dict:
    """Fully replace the section's stored fields with ``fields`` (PUT
    semantics, unlike ``patch_section``'s partial-merge PATCH semantics).
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    merged = {**fields, "updated_at": now}
    table = get_table()
    table.put_item(
        Item={
            "PK": _profile_pk(profile_id),
            "SK": _section_sk(section),
            "entityType": "ProfileSection",
            **merged,
        }
    )
    return merged
