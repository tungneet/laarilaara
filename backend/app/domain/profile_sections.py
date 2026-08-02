"""Controlled-value enums for profile sections (catalog §5 — "Sections",
batch: personal-details, narratives, lifestyle, visibility).
"""
from __future__ import annotations

from enum import Enum


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class MaritalStatus(str, Enum):
    NEVER_MARRIED = "never_married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"
    ANNULLED = "annulled"


class DietType(str, Enum):
    VEGETARIAN = "vegetarian"
    EGGETARIAN = "eggetarian"
    NON_VEGETARIAN = "non_vegetarian"
    VEGAN = "vegan"
    OTHER = "other"


class HabitLevel(str, Enum):
    NO = "no"
    OCCASIONALLY = "occasionally"
    YES = "yes"


class VisibilityLevel(str, Enum):
    PUBLIC = "public"
    MANAGERS_ONLY = "managers_only"
    CONNECTIONS_ONLY = "connections_only"


class FamilyType(str, Enum):
    NUCLEAR = "nuclear"
    JOINT = "joint"
    EXTENDED = "extended"
    OTHER = "other"


class FamilyMemberRelation(str, Enum):
    FATHER = "father"
    MOTHER = "mother"
    BROTHER = "brother"
    SISTER = "sister"
    OTHER = "other"
