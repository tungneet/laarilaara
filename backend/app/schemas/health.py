"""Shared response models used across routers."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class DependencyStatus(BaseModel):
    name: str
    status: Literal["ok", "skipped", "error"]
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"]
    checks: list[DependencyStatus]
