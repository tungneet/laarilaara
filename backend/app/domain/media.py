"""Controlled-value enums for media and generated documents (catalog §6:
"Media and generated documents").
"""
from __future__ import annotations

from enum import Enum


class MediaAssetStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    DELETED = "deleted"


class BiodataStatus(str, Enum):
    QUEUED = "queued"
    READY = "ready"
    FAILED = "failed"
