"""RFC 9457 (problem+json) error handling.

Every error response across the API uses `application/problem+json` with a
stable shape: `type`, `title`, `status`, `code`, `detail`, `instance`,
`requestId`, and an optional `errors` array for field-level validation.

The catalog (../documents/lambda-based/04-api-catalog.md §16) defines the status
codes and the stable domain `code` values.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE = "https://laarilaara.com/problems/"


class ApiError(Exception):
    """Domain error that maps to a problem+json response.

    `code` is a stable machine-readable identifier (for example
    ``PROFILE_NOT_PUBLISHABLE``); `status` is the HTTP status code.
    """

    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        detail: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(detail or title)
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.errors = errors


def _problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str | None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}{code.lower()}",
        "title": title,
        "status": status,
        "code": code,
        "instance": str(request.url.path),
        "requestId": request_id,
    }
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors

    headers = {"Content-Type": PROBLEM_CONTENT_TYPE}
    if request_id:
        headers["X-Request-Id"] = request_id

    return JSONResponse(status_code=status, content=body, headers=headers)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _problem_response(
        request,
        status=exc.status,
        code=exc.code,
        title=exc.title,
        detail=exc.detail,
        errors=exc.errors,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    title = exc.detail if isinstance(exc.detail, str) else "HTTP error"
    return _problem_response(
        request,
        status=exc.status_code,
        code=_status_to_code(exc.status_code),
        title=title,
        detail=None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in err.get("loc", []) if part != "body"),
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        }
        for err in exc.errors()
    ]
    return _problem_response(
        request,
        status=422,
        code="VALIDATION_FAILED",
        title="Request validation failed",
        detail="One or more fields are invalid.",
        errors=errors,
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    # Never leak internal details to the client.
    return _problem_response(
        request,
        status=500,
        code="INTERNAL_ERROR",
        title="Internal server error",
        detail=None,
    )


def _status_to_code(status: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        412: "PRECONDITION_FAILED",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        503: "SERVICE_UNAVAILABLE",
    }.get(status, "ERROR")
