"""In-process WebSocket connection manager for local/dev use.

Catalog §9 assumes AWS API Gateway WebSocket API, where connections are held
by API Gateway itself (not by any Lambda) and server->client push goes
through the `PostToConnection` Management API call. There is no equivalent
out-of-process fan-out available when running this app as a single local
`uvicorn`/pytest process, so this module holds live `WebSocket` objects
in memory for the lifetime of *this* process only.

This is intentionally NOT relied upon for correctness across concurrent
Lambda invocations — see `app/services/realtime.py::push_event`, which is
the seam a real AWS deployment would replace with a boto3
`apigatewaymanagementapi` client call keyed off the connection row's stored
`api_gateway_endpoint`, instead of this in-memory manager.
"""
from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._active: dict[str, WebSocket] = {}

    def connect(self, connection_id: str, websocket: WebSocket) -> None:
        self._active[connection_id] = websocket

    def disconnect(self, connection_id: str) -> None:
        self._active.pop(connection_id, None)

    async def send(self, connection_id: str, event: dict) -> bool:
        """Return False (analogous to AWS `GoneException`/410) if the
        connection isn't live in this process anymore.
        """
        websocket = self._active.get(connection_id)
        if websocket is None:
            return False
        await websocket.send_json(event)
        return True


manager = ConnectionManager()
