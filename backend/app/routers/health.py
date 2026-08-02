"""Health endpoints.

- GET /health/live  : cheap liveness; no dependency calls.
- GET /health/ready : readiness; checks critical dependencies (DynamoDB) when
  enabled. Returns 503 with a problem+json body when a critical dependency is
  unavailable so API Gateway canaries and deploy checks fail fast.

See ../documents/lambda-based/04-api-catalog.md §3.
"""
from __future__ import annotations

from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.health import (
    DependencyStatus,
    LivenessResponse,
    ReadinessResponse,
)

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health/live", response_model=LivenessResponse)
async def live() -> LivenessResponse:
    return LivenessResponse()


@router.get("/health/ready", response_model=ReadinessResponse)
async def ready(response: Response) -> ReadinessResponse:
    checks: list[DependencyStatus] = [_check_dynamodb()]

    is_ready = all(check.status in ("ok", "skipped") for check in checks)
    if not is_ready:
        response.status_code = 503

    return ReadinessResponse(
        status="ready" if is_ready else "degraded",
        checks=checks,
    )


def _check_dynamodb() -> DependencyStatus:
    settings = get_settings()
    if not settings.check_dependencies_on_ready:
        return DependencyStatus(
            name="dynamodb",
            status="skipped",
            detail="dependency checks disabled for this environment",
        )

    try:
        import boto3  # imported lazily so local/tests need no AWS SDK

        client = boto3.client(
            "dynamodb",
            region_name=settings.aws_region,
            endpoint_url=settings.storage.dynamodb_endpoint_url,
        )
        client.describe_table(TableName=settings.storage.dynamodb_table_name)
        return DependencyStatus(name="dynamodb", status="ok")
    except Exception as exc:  # noqa: BLE001 - readiness must never raise
        logger.error("dynamodb readiness check failed: %s", exc)
        return DependencyStatus(
            name="dynamodb",
            status="error",
            detail="table not reachable",
        )
