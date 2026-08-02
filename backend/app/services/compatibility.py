"""Compatibility analysis service (catalog §8:
`POST /v1/compatibility-analyses`, `GET /v1/compatibility-analyses/{analysisId}`).

KNOWN SIMPLIFICATION: there is no ML/embedding-based compatibility model in
this codebase (the architecture notes describe an embeddings pipeline with
daily-batch pairwise rebuild, none of which is built yet). `_score` is a
deterministic, explainable placeholder based on age closeness, shared
communities, and lifestyle (diet) match — good enough to exercise the full
create/refresh/get flow and satisfy "deterministic compatibility score"
from repo memory, but must be replaced once the real embeddings pipeline
exists.

Since scoring is synchronous and cheap, `create_or_refresh_analysis` always
computes and returns the result directly (HTTP 200) rather than the
catalog's alternate `202` (queued) path — there is no async worker to defer
to yet.
"""
from __future__ import annotations

from datetime import date

from app.repositories import compatibility_analyses as analyses_repo
from app.repositories import profile_sections as sections_repo
from app.repositories import profile_sets as sets_repo
from app.services import profiles as profiles_service

_PERSONAL_DETAILS = "PERSONAL_DETAILS"
_LIFESTYLE = "LIFESTYLE"
_COMMUNITIES = "COMMUNITIES"


class AnalysisNotFoundError(Exception):
    pass


def _age(date_of_birth) -> int | None:
    if date_of_birth is None:
        return None
    if isinstance(date_of_birth, str):
        date_of_birth = date.fromisoformat(date_of_birth)
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def _age_compatibility(profile_a_id: str, profile_b_id: str) -> int:
    age_a = _age(sections_repo.get_section(profile_a_id, _PERSONAL_DETAILS).get("date_of_birth"))
    age_b = _age(sections_repo.get_section(profile_b_id, _PERSONAL_DETAILS).get("date_of_birth"))
    if age_a is None or age_b is None:
        return 0
    diff = abs(age_a - age_b)
    return max(0, 100 - diff * 5)


def _community_overlap(profile_a_id: str, profile_b_id: str) -> int:
    a = set(sets_repo.get_set(profile_a_id, _COMMUNITIES)["values"])
    b = set(sets_repo.get_set(profile_b_id, _COMMUNITIES)["values"])
    if not a or not b:
        return 0
    return round(100 * len(a & b) / len(a | b))


def _lifestyle_compatibility(profile_a_id: str, profile_b_id: str) -> int:
    diet_a = sections_repo.get_section(profile_a_id, _LIFESTYLE).get("diet")
    diet_b = sections_repo.get_section(profile_b_id, _LIFESTYLE).get("diet")
    if diet_a is None or diet_b is None:
        return 0
    return 100 if diet_a == diet_b else 40


def _compute(acting_profile_id: str, target_profile_id: str) -> tuple[int, dict]:
    factors = {
        "age_compatibility": _age_compatibility(acting_profile_id, target_profile_id),
        "community_overlap": _community_overlap(acting_profile_id, target_profile_id),
        "lifestyle_compatibility": _lifestyle_compatibility(acting_profile_id, target_profile_id),
    }
    score = round(sum(factors.values()) / len(factors))
    return score, factors


def create_or_refresh_analysis(account_id: str, acting_profile_id: str, target_profile_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)
    profiles_service.get_or_404(target_profile_id)

    score, factors = _compute(acting_profile_id, target_profile_id)
    return analyses_repo.upsert_analysis(acting_profile_id, target_profile_id, score, factors)


def get_analysis(account_id: str, acting_profile_id: str, analysis_id: str) -> dict:
    profiles_service.require_permission(acting_profile_id, account_id, "profile.read_private")
    profiles_service.get_or_404(acting_profile_id)

    analysis = analyses_repo.get_analysis(analysis_id)
    if analysis is None or analysis["acting_profile_id"] != acting_profile_id:
        # Mask existence: an analysis belonging to a different acting profile
        # looks identical to one that doesn't exist.
        raise AnalysisNotFoundError(analysis_id)
    return analysis
