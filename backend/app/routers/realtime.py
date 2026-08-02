"""Router for the realtime WebSocket half (catalog §9):
`POST /v1/realtime-tokens`, plus a local-dev `$connect`/`$default`/`$disconnect`
equivalent as a native FastAPI WebSocket route.

On AWS this WebSocket route does not exist — `$connect`/`$disconnect`/
`$default` are separate API Gateway WebSocket API Lambda integrations, not
reachable through the Mangum ASGI adapter this REST API uses. This
route exists so the connection-registry/push/typing-dispatch logic in
`app/services/realtime.py` is exercisable locally and under pytest via
Starlette's `TestClient.websocket_connect`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from app.core.dependencies import CurrentSession, get_current_session
from app.core.errors import ApiError
from app.core.realtime_manager import manager
from app.schemas.realtime import RealtimeTokenRequest, RealtimeTokenResponse
from app.services import profiles as profiles_service
from app.services import realtime as realtime_service

router = APIRouter(tags=["realtime"])

_PROFILE_NOT_FOUND_ERROR = ApiError(
    status=status.HTTP_404_NOT_FOUND, code="PROFILE_NOT_FOUND", title="Profile not found"
)
_PROFILE_FORBIDDEN_ERROR = ApiError(
    status=status.HTTP_403_FORBIDDEN,
    code="PROFILE_FORBIDDEN",
    title="You do not have permission to act as this profile",
)

_CONNECT_POLICY_VIOLATION = 1008  # WebSocket close code: policy violation


@router.post(
    "/v1/realtime-tokens", response_model=RealtimeTokenResponse, status_code=status.HTTP_201_CREATED
)
async def create_realtime_token(
    payload: RealtimeTokenRequest,
    current: CurrentSession = Depends(get_current_session),
) -> RealtimeTokenResponse:
    try:
        token, expires_in = realtime_service.issue_token(current.account_id, payload.profile_id)
    except profiles_service.ProfileNotFoundError as exc:
        raise _PROFILE_NOT_FOUND_ERROR from exc
    except profiles_service.ProfileForbiddenError as exc:
        raise _PROFILE_FORBIDDEN_ERROR from exc
    return RealtimeTokenResponse(token=token, expires_in=expires_in)


@router.websocket("/v1/realtime")
async def realtime_socket(websocket: WebSocket, token: str = Query(...)) -> None:
    try:
        account_id, profile_id = realtime_service.resolve_connect_token(token)
    except realtime_service.RealtimeTokenInvalidError:
        await websocket.close(code=_CONNECT_POLICY_VIOLATION)
        return

    await websocket.accept()
    connection_id = realtime_service.register_connection(account_id, profile_id)
    manager.connect(connection_id, websocket)

    try:
        while True:
            frame = await websocket.receive_json()
            action = frame.get("action")
            conversation_id = frame.get("conversationId")
            if action and conversation_id:
                await realtime_service.handle_client_action(conversation_id, profile_id, action)
    except WebSocketDisconnect:
        pass
    finally:
        realtime_service.unregister_connection(profile_id, connection_id)
