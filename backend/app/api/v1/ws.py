import json
import logging
from typing import Optional
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from backend.app.core.database import async_session_maker
from backend.app.core.security import decode_access_token
from backend.app.schemas.ws_messages import WSMessage, WSMessageType
from backend.app.services.auth_service import auth_service
from backend.app.services.board_service import board_service
from backend.app.services.collaboration_engine import collaboration_engine
from backend.app.services.connection_manager import manager

logger = logging.getLogger("kanvaset.ws")
router = APIRouter(tags=["WebSockets"])

PALETTE = [
    "#EF4444", "#F59E0B", "#10B981", "#3B82F6",
    "#6366F1", "#8B5CF6", "#EC4899", "#14B8A6",
    "#F97316", "#06B6D4"
]


def pick_color(user_id: str) -> str:
    return PALETTE[abs(hash(user_id)) % len(PALETTE)]


@router.websocket("/ws/boards/{board_id}")
async def board_websocket_endpoint(
    websocket: WebSocket,
    board_id: str,
    token: Optional[str] = Query(None),
):
    # 1. Extract and validate authentication token
    token_str = token
    if not token_str:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token_str = auth_header[7:]

    if not token_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")
        return

    payload = decode_access_token(token_str)
    if not payload or "sub" not in payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid auth token")
        return

    user_id = payload["sub"]

    # 2. Check user and board authorization
    async with async_session_maker() as db:
        user = await auth_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User unauthorized")
            return

        role = await board_service.check_board_access(db, board_id, user_id)
        if not role:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Forbidden board access")
            return

        username = user.username
        user_color = pick_color(user.id)

    # 3. Accept and register connection
    client = await manager.connect(
        board_id=board_id,
        websocket=websocket,
        user_id=user_id,
        username=username,
        role=role,
        color=user_color,
    )

    try:
        # 4. Send initial SYNC_SNAPSHOT to the connecting client
        async with async_session_maker() as db:
            snapshot_data = await board_service.get_board_snapshot(db, board_id, user_id)
            snapshot_msg = WSMessage(
                type=WSMessageType.SYNC_SNAPSHOT,
                board_id=board_id,
                server_revision=snapshot_data["server_revision"],
                payload=snapshot_data
            )
            await websocket.send_text(json.dumps(snapshot_msg.model_dump()))

        # 5. Receive & dispatch loop
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                msg = WSMessage.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as e:
                err_msg = WSMessage(
                    type=WSMessageType.ERROR,
                    board_id=board_id,
                    payload={"detail": f"Malformed WebSocket payload: {str(e)}"}
                )
                await websocket.send_text(json.dumps(err_msg.model_dump()))
                continue

            # Ensure board_id matches URL
            msg.board_id = board_id

            # Ephemeral: Live Cursor Movement
            if msg.type == WSMessageType.CURSOR_MOVED:
                cursor_payload = msg.payload or {}
                cursor_msg = WSMessage(
                    type=WSMessageType.CURSOR_MOVED,
                    board_id=board_id,
                    user_id=user_id,
                    user_name=username,
                    user_color=user_color,
                    payload={
                        "x": cursor_payload.get("x", 0),
                        "y": cursor_payload.get("y", 0),
                        "user_id": user_id,
                        "user_name": username,
                        "user_color": user_color,
                    }
                )
                # Broadcast cursor to other clients
                await manager.broadcast_global(board_id, cursor_msg.model_dump())
                continue

            # State Recovery: Full Snapshot Request
            if msg.type == WSMessageType.SYNC_REQUEST:
                async with async_session_maker() as db:
                    snapshot_data = await board_service.get_board_snapshot(db, board_id, user_id)
                    snapshot_resp = WSMessage(
                        type=WSMessageType.SYNC_SNAPSHOT,
                        board_id=board_id,
                        server_revision=snapshot_data["server_revision"],
                        payload=snapshot_data
                    )
                    await websocket.send_text(json.dumps(snapshot_resp.model_dump()))
                continue

            # Semantic Mutation Operations
            if msg.type in [
                WSMessageType.OBJECT_CREATED,
                WSMessageType.OBJECT_MOVED,
                WSMessageType.OBJECT_RESIZED,
                WSMessageType.OBJECT_UPDATED,
                WSMessageType.OBJECT_DELETED,
            ]:
                try:
                    async with async_session_maker() as db:
                        broadcast_msg, err_detail = await collaboration_engine.process_operation(
                            db=db,
                            msg=msg,
                            user_id=user_id,
                            user_name=username,
                            role=role
                        )
                        if err_detail:
                            err_resp = WSMessage(
                                type=WSMessageType.ERROR,
                                board_id=board_id,
                                operation_id=msg.operation_id,
                                payload={"detail": err_detail}
                            )
                            await websocket.send_text(json.dumps(err_resp.model_dump()))
                        elif broadcast_msg:
                            await db.commit()
                            # Broadcast mutation to room
                            await manager.broadcast_global(board_id, broadcast_msg.model_dump())

                            # Send ACK to sender
                            ack_resp = WSMessage(
                                type=WSMessageType.ACK,
                                board_id=board_id,
                                operation_id=msg.operation_id,
                                server_revision=broadcast_msg.server_revision,
                            )
                            await websocket.send_text(json.dumps(ack_resp.model_dump()))
                except Exception as op_err:
                    logger.exception("Error processing operation %s: %s", msg.operation_id, op_err)
                    err_resp = WSMessage(
                        type=WSMessageType.ERROR,
                        board_id=board_id,
                        operation_id=msg.operation_id,
                        payload={"detail": f"Operation processing error: {str(op_err)}"}
                    )
                    await websocket.send_text(json.dumps(err_resp.model_dump()))

    except WebSocketDisconnect:
        await manager.disconnect(board_id, client)
    except Exception as e:
        logger.exception("Unexpected error on websocket for board %s: %s", board_id, e)
        await manager.disconnect(board_id, client)
