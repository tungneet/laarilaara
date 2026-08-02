"""Profile aggregate and lifecycle service (catalog §5 — first block).

Permission model here is intentionally minimal: a profile's creating account
is its ``owner`` manager with every permission. The full manager
invite/accept/permission-editing system is a later batch; until then, the
only accounts that can act on a profile are ones with a manager row (i.e.
today, only the owner).

Known simplifications (documented for the next batch to revisit):
- ``submit`` does not yet validate age/consent/required media, since the
  personal-details, consent-linkage, and media sections don't exist yet.
- ``delete_profile`` does not enforce "recent auth" (no step-up auth flow
  built yet) or legal/policy holds (no policy engine yet).
- ``completion``/``preview`` are stubs: since no sections exist yet, they
  report all sections as missing / a placeholder preview. Both will be
  extended as each section is implemented.
"""
from __future__ import annotations

from app.domain.profiles import Profile, ProfileRelationship, ProfileStatus
from app.repositories import profile_managers as managers_repo
from app.repositories import profiles as profiles_repo

REQUIRED_SECTIONS = [
    "personal_details",
    "narratives",
    "lifestyle",
    "visibility",
    "education",
    "employment",
    "family",
    "preferences",
]


class ProfileNotFoundError(Exception):
    pass


class ProfileForbiddenError(Exception):
    pass


class ProfileStateConflictError(Exception):
    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"expected status in {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


def require_permission(profile_id: str, account_id: str, permission: str) -> dict:
    """Return the caller's manager row if they hold ``permission``.

    Raises ``ProfileNotFoundError`` (masking existence) if the account has no
    manager row at all, or ``ProfileForbiddenError`` if it lacks the permission.
    """
    manager = managers_repo.get_manager(profile_id, account_id)
    if manager is None:
        # Mask existence: an account with no manager row cannot tell whether
        # the profile exists at all.
        raise ProfileNotFoundError(profile_id)
    if permission not in manager.get("permissions", []):
        raise ProfileForbiddenError(permission)
    return manager


def get_or_404(profile_id: str) -> Profile:
    profile = profiles_repo.get_profile(profile_id)
    if profile is None:
        raise ProfileNotFoundError(profile_id)
    return profile


def create_profile(account_id: str, relationship: str, locale: str = "en") -> Profile:
    rel = ProfileRelationship(relationship)
    if rel is ProfileRelationship.SELF:
        existing_id = managers_repo.find_self_profile_id(account_id)
        if existing_id is not None:
            existing = profiles_repo.get_profile(existing_id)
            if existing is not None:
                return existing

    profile = profiles_repo.create_profile(account_id, rel, locale)
    managers_repo.create_owner_manager(
        profile.id, account_id, is_self_profile=rel is ProfileRelationship.SELF
    )
    return profile


def get_profile(account_id: str, profile_id: str) -> Profile:
    require_permission(profile_id, account_id, "profile.read_private")
    return get_or_404(profile_id)


def list_my_profiles(account_id: str) -> list[tuple[Profile, dict]]:
    """Every profile this account manages, with its manager row.

    Backs ``GET /v1/me/profiles`` — the UI's entry point for choosing an
    acting profile after login (profile ids are otherwise only returned at
    creation time).
    """
    results: list[tuple[Profile, dict]] = []
    for manager in managers_repo.list_manager_rows_for_account(account_id):
        profile_id = manager["PK"].removeprefix("PROFILE#")
        profile = profiles_repo.get_profile(profile_id)
        if profile is not None and profile.status is not ProfileStatus.DELETING:
            results.append((profile, manager))
    results.sort(key=lambda pair: pair[0].created_at)
    return results


def patch_profile(account_id: str, profile_id: str, locale: str) -> Profile:
    require_permission(profile_id, account_id, "profile.edit")
    get_or_404(profile_id)
    return profiles_repo.update_locale(profile_id, locale)


def preview_profile(account_id: str, profile_id: str) -> dict:
    require_permission(profile_id, account_id, "profile.read_private")
    profile = get_or_404(profile_id)
    return {
        "profile_id": profile.id,
        "status": profile.status.value,
        "locale": profile.locale,
        "note": (
            "Preview will include published sections once profile sections "
            "are implemented."
        ),
    }


def get_completion(account_id: str, profile_id: str) -> dict:
    require_permission(profile_id, account_id, "profile.read_private")
    profile = get_or_404(profile_id)

    from app.repositories import profile_records as records_repo
    from app.repositories import profile_sections as sections_repo

    def _section_filled(name: str) -> bool:
        fields = sections_repo.get_section(profile_id, name)
        return any(
            value is not None and value != "" and value != []
            for key, value in fields.items()
            if key != "updated_at"
        )

    checks: dict[str, bool] = {
        "personal_details": _section_filled("PERSONAL_DETAILS"),
        "narratives": _section_filled("NARRATIVES"),
        "lifestyle": _section_filled("LIFESTYLE"),
        "visibility": _section_filled("VISIBILITY"),
        "education": len(records_repo.list_records(profile_id, "EDUCATION")) > 0,
        "employment": len(records_repo.list_records(profile_id, "EMPLOYMENT")) > 0,
        "family": _section_filled("FAMILY"),
        "preferences": _section_filled("PREFERENCES"),
    }

    missing = [name for name in REQUIRED_SECTIONS if not checks.get(name, False)]
    score = round(100 * (len(checks) - len(missing)) / len(checks))
    return {
        "profile_id": profile.id,
        "score": score,
        "missing_sections": missing,
    }


def submit_profile(account_id: str, profile_id: str) -> Profile:
    require_permission(profile_id, account_id, "profile.edit")
    profile = get_or_404(profile_id)
    if profile.status is not ProfileStatus.DRAFT:
        raise ProfileStateConflictError("draft", profile.status.value)
    return profiles_repo.set_status(
        profile_id, ProfileStatus.PENDING_REVIEW, timestamp_field="submittedAt"
    )


def publish_profile(account_id: str, profile_id: str) -> Profile:
    require_permission(profile_id, account_id, "profile.publish")
    profile = get_or_404(profile_id)
    if profile.status is ProfileStatus.PUBLISHED:
        return profile
    if profile.status is not ProfileStatus.PENDING_REVIEW:
        raise ProfileStateConflictError("pending_review", profile.status.value)
    return profiles_repo.set_status(
        profile_id, ProfileStatus.PUBLISHED, timestamp_field="publishedAt"
    )


def pause_profile(account_id: str, profile_id: str) -> Profile:
    require_permission(profile_id, account_id, "profile.publish")
    profile = get_or_404(profile_id)
    if profile.status is not ProfileStatus.PUBLISHED:
        raise ProfileStateConflictError("published", profile.status.value)
    return profiles_repo.set_status(
        profile_id, ProfileStatus.PAUSED, timestamp_field="pausedAt"
    )


def resume_profile(account_id: str, profile_id: str) -> Profile:
    require_permission(profile_id, account_id, "profile.publish")
    profile = get_or_404(profile_id)
    if profile.status is not ProfileStatus.PAUSED:
        raise ProfileStateConflictError("paused", profile.status.value)
    return profiles_repo.set_status(
        profile_id, ProfileStatus.PUBLISHED, timestamp_field="publishedAt"
    )


def delete_profile(account_id: str, profile_id: str) -> Profile:
    require_permission(profile_id, account_id, "profile.edit")
    profile = get_or_404(profile_id)
    if profile.status is ProfileStatus.DELETING:
        return profile
    return profiles_repo.set_status(profile_id, ProfileStatus.DELETING)
