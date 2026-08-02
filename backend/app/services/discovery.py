"""Discovery service: search, public profile projection, recommendations,
and view recording (catalog §7).

KNOWN SIMPLIFICATIONS (documented for later):
- No real search index exists (see `profiles_repo.list_published_profiles`
  docstring) — filtering is a Python-side linear scan, fine at dev scale.
- No embedding-based recommendation engine exists yet (deferred daily-batch
  EventBridge->Lambda job per architecture notes); "recommendations" here is
  the same published-profile pool as search with no filters, in deterministic
  `id` order — satisfies the catalog's "MVP may use deterministic ranking".
- No block/report system exists yet, so there is nothing to enforce policy
  filtering against beyond "is the target published" and "has the viewer
  hidden this target from their own discovery view".
- The "safe public projection" field list (age/gender/height/marital
  status/headline/bio) is an inferred reasonable subset, not an authoritative
  per-field visibility mapping (same open gap already flagged for the
  `visibility` section in catalog §5 batch A).
"""
from __future__ import annotations

from datetime import date

from app.core.pagination import decode_cursor as _decode_cursor
from app.core.pagination import encode_cursor as _encode_cursor
from app.repositories import profile_sections as sections_repo
from app.repositories import profile_sets as sets_repo
from app.repositories import profile_target_links as links_repo
from app.repositories import profile_views as views_repo
from app.repositories import profiles as profiles_repo
from app.services import profiles as profiles_service

_HIDDEN = "HIDDEN"
_PERSONAL_DETAILS = "PERSONAL_DETAILS"
_NARRATIVES = "NARRATIVES"
_COMMUNITIES = "COMMUNITIES"


class TargetProfileNotFoundError(Exception):
    pass


def _age(date_of_birth: date | None) -> int | None:
    if date_of_birth is None:
        return None
    if isinstance(date_of_birth, str):
        date_of_birth = date.fromisoformat(date_of_birth)
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _project_summary(profile_id: str) -> dict:
    personal = sections_repo.get_section(profile_id, _PERSONAL_DETAILS)
    narratives = sections_repo.get_section(profile_id, _NARRATIVES)
    return {
        "profile_id": profile_id,
        "age": _age(personal.get("date_of_birth")),
        "gender": personal.get("gender"),
        "height_cm": personal.get("height_cm"),
        "marital_status": personal.get("marital_status"),
        "headline": narratives.get("headline"),
    }


def _project_detail(profile_id: str) -> dict:
    summary = _project_summary(profile_id)
    narratives = sections_repo.get_section(profile_id, _NARRATIVES)
    return {**summary, "bio": narratives.get("bio")}


def _candidate_pool(acting_profile_id: str) -> list[str]:
    hidden_ids = {link["target_profile_id"] for link in links_repo.list_links(acting_profile_id, _HIDDEN)}
    published = profiles_repo.list_published_profiles()
    candidates = [p.id for p in sorted(published, key=lambda p: p.id) if p.id != acting_profile_id]
    return [pid for pid in candidates if pid not in hidden_ids]


def _matches_filters(profile_id: str, filters: dict) -> bool:
    personal = sections_repo.get_section(profile_id, _PERSONAL_DETAILS)
    age = _age(personal.get("date_of_birth"))
    if filters.get("min_age") is not None and (age is None or age < filters["min_age"]):
        return False
    if filters.get("max_age") is not None and (age is None or age > filters["max_age"]):
        return False
    if filters.get("gender") is not None and personal.get("gender") != filters["gender"]:
        return False
    communities = filters.get("communities")
    if communities:
        profile_communities = set(sets_repo.get_set(profile_id, _COMMUNITIES)["values"])
        if not profile_communities.intersection(communities):
            return False
    return True


def search(account_id: str, acting_profile_id: str, filters: dict, cursor: str | None, limit: int) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    candidates = [pid for pid in _candidate_pool(acting_profile_id) if _matches_filters(pid, filters)]
    offset = _decode_cursor(cursor)
    page = candidates[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(candidates) else None
    return {"items": [_project_summary(pid) for pid in page], "next_cursor": next_cursor}


def recommendations(account_id: str, acting_profile_id: str, cursor: str | None, limit: int) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    candidates = _candidate_pool(acting_profile_id)
    offset = _decode_cursor(cursor)
    page = candidates[offset : offset + limit]
    next_cursor = _encode_cursor(offset + limit) if offset + limit < len(candidates) else None
    return {"items": [_project_summary(pid) for pid in page], "next_cursor": next_cursor}


def get_public_profile(account_id: str, acting_profile_id: str, target_profile_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    target = profiles_repo.get_profile(target_profile_id)
    if target is None or target.status.value != "published":
        raise TargetProfileNotFoundError(target_profile_id)
    return _project_detail(target_profile_id)


def record_view(account_id: str, acting_profile_id: str, target_profile_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)
    profiles_service.get_or_404(target_profile_id)

    return views_repo.record_view(acting_profile_id, target_profile_id)
