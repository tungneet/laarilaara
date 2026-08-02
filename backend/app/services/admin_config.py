"""Admin brands/experiences/feature-flags config service (catalog §15
"Brands/config"). GET/PATCH only — no create; see the repo docstrings for
the seed-out-of-band convention.
"""
from __future__ import annotations

from app.repositories import admin_audit as admin_audit_repo
from app.repositories import brand_configs as brand_configs_repo
from app.repositories import experience_configs as experience_configs_repo
from app.repositories import feature_flags as feature_flags_repo


class BrandConfigNotFoundError(Exception):
    pass


class ExperienceConfigNotFoundError(Exception):
    pass


class FeatureFlagNotFoundError(Exception):
    pass


def get_brand(brand_id: str) -> dict:
    brand = brand_configs_repo.get_brand(brand_id)
    if brand is None:
        raise BrandConfigNotFoundError(brand_id)
    return brand


def update_brand(admin_account_id: str, brand_id: str, name: str | None, active: bool | None, reason: str) -> dict:
    get_brand(brand_id)
    updated = brand_configs_repo.update_brand(brand_id, name, active)
    assert updated is not None
    admin_audit_repo.record(admin_account_id, "config.brand.update", "brand_config", brand_id, reason)
    return updated


def get_experience(experience_id: str) -> dict:
    experience = experience_configs_repo.get_experience(experience_id)
    if experience is None:
        raise ExperienceConfigNotFoundError(experience_id)
    return experience


def update_experience(
    admin_account_id: str, experience_id: str, name: str | None, active: bool | None, reason: str
) -> dict:
    get_experience(experience_id)
    updated = experience_configs_repo.update_experience(experience_id, name, active)
    assert updated is not None
    admin_audit_repo.record(
        admin_account_id, "config.experience.update", "experience_config", experience_id, reason
    )
    return updated


def get_feature_flag(key: str) -> dict:
    flag = feature_flags_repo.get_flag(key)
    if flag is None:
        raise FeatureFlagNotFoundError(key)
    return flag


def update_feature_flag(admin_account_id: str, key: str, enabled: bool, reason: str) -> dict:
    get_feature_flag(key)
    updated = feature_flags_repo.update_flag(key, enabled)
    assert updated is not None
    admin_audit_repo.record(admin_account_id, "config.feature_flag.update", "feature_flag", key, reason)
    return updated
