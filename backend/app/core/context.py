"""Request context middleware.

Assigns a correlation id to every request (honoring a valid inbound
`X-Request-Id`/`X-Amzn-Trace-Id` or generating one), stores it on
`request.state.request_id`, echoes it back on the response, and makes it
available to the JSON logger.
"""
from __future__ import annotations

import re
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REQUEST_ID_HEADER = "X-Request-Id"
_TRACE_HEADER = "X-Amzn-Trace-Id"
# Accept only safe, bounded correlation ids to avoid log injection.
_SAFE_ID = re.compile(r"^[A-Za-z0-9._=-]{1,128}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = self._resolve_request_id(request)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response

    @staticmethod
    def _resolve_request_id(request: Request) -> str:
        candidate = request.headers.get(_REQUEST_ID_HEADER)
        if candidate and _SAFE_ID.match(candidate):
            return candidate

        trace = request.headers.get(_TRACE_HEADER)
        if trace and _SAFE_ID.match(trace):
            return trace

        return uuid.uuid4().hex
