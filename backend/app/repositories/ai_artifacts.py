"""AI artifact + operation repository (catalog §10, AI-assisted domain endpoints).

Item shapes (single table):

- Artifact: ``PK = ARTIFACT#{id}``  ``SK = ARTIFACT``
  Doubles as the shared ``Operation`` resource (catalog §2) for these
  endpoints — there is exactly one row per generation request, and its
  ``status`` field follows the Operation state machine
  (``queued``/``running``/``succeeded``/``failed``/``canceled``/``expired``).
- Feedback: ``PK = ARTIFACT#{id}``  ``SK = FEEDBACK#{profileId}``
  One row per (artifact, submitting profile) — a repeat submission
  overwrites the previous one (idempotent per catalog note).

Artifacts are created `queued`, then immediately transitioned to
``succeeded``/``failed`` by `app.services.ai` via the central
`app.core.ai_engine` (synchronous inline execution — no SQS/EventBridge
worker exists anywhere in this codebase, so there is no separate async
completion step).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.dynamodb import get_table


def _pk(artifact_id: str) -> str:
    return f"ARTIFACT#{artifact_id}"


def _strip(item: dict) -> dict:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "entityType")}


def create_artifact(
    kind: str,
    owner_profile_id: str,
    subject: dict,
    input_payload: dict,
) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    artifact_id = str(uuid.uuid4())
    item = {
        "PK": _pk(artifact_id),
        "SK": "ARTIFACT",
        "entityType": "AiArtifact",
        "id": artifact_id,
        "kind": kind,
        "status": "queued",
        "owner_profile_id": owner_profile_id,
        "subject": subject,
        "input": input_payload,
        "result": None,
        "error": None,
        "created_at": now,
        "completed_at": None,
    }
    table.put_item(Item=item)
    return _strip(item)


def get_artifact(artifact_id: str) -> dict | None:
    table = get_table()
    resp = table.get_item(Key={"PK": _pk(artifact_id), "SK": "ARTIFACT"})
    item = resp.get("Item")
    return _strip(item) if item else None


def mark_succeeded(artifact_id: str, result: dict) -> dict:
    """Transition an artifact to `succeeded` with its generated result.

    Called synchronously right after `create_artifact` by `app.services.ai`
    (via the central `app.core.ai_engine`) since no async worker exists in
    this codebase — `status`/`result` are aliased because `status` is a
    reserved word in DynamoDB expression syntax.
    """
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(artifact_id), "SK": "ARTIFACT"},
        UpdateExpression="SET #status = :status, #result = :result, completed_at = :completed_at",
        ExpressionAttributeNames={"#status": "status", "#result": "result"},
        ExpressionAttributeValues={":status": "succeeded", ":result": result, ":completed_at": now},
    )
    return get_artifact(artifact_id)  # type: ignore[return-value]


def mark_failed(artifact_id: str, error: dict) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    table.update_item(
        Key={"PK": _pk(artifact_id), "SK": "ARTIFACT"},
        UpdateExpression="SET #status = :status, #error = :error, completed_at = :completed_at",
        ExpressionAttributeNames={"#status": "status", "#error": "error"},
        ExpressionAttributeValues={":status": "failed", ":error": error, ":completed_at": now},
    )
    return get_artifact(artifact_id)  # type: ignore[return-value]


def put_feedback(artifact_id: str, profile_id: str, rating: int, category: str | None) -> dict:
    table = get_table()
    now = datetime.now(tz=timezone.utc).isoformat()
    item = {
        "PK": _pk(artifact_id),
        "SK": f"FEEDBACK#{profile_id}",
        "entityType": "AiArtifactFeedback",
        "artifact_id": artifact_id,
        "profile_id": profile_id,
        "rating": rating,
        "category": category,
        "created_at": now,
    }
    table.put_item(Item=item)
    return _strip(item)
