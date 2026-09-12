import asyncio
import json
import pytest
from starlette.testclient import TestClient
from backend.app.core.config import settings

# Test DB settings
TEST_DB_FILE = "test_kanvaset.db"
settings.DATABASE_URL = f"sqlite+aiosqlite:///./{TEST_DB_FILE}"
settings.USE_REDIS = False
settings.SECRET_KEY = "test_secret_key_for_unit_tests_only_123456789"

from backend.app.core.database import Base, engine, async_session_maker
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.main import app
from backend.app.models.board import Board, BoardMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_websocket_flow(db_session):
    # 1. Seed user, workspace, and board in the async db session
    user = User(
        email="ws_user@example.com",
        username="ws_user",
        hashed_password=get_password_hash("password123"),
    )
    unauth_user = User(
        email="ws_unauth@example.com",
        username="ws_unauth",
        hashed_password=get_password_hash("password123"),
    )
    db_session.add_all([user, unauth_user])
    await db_session.flush()

    ws = Workspace(name="WS Studio", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    board = Board(workspace_id=ws.id, name="Live Collab Board", created_by=user.id, revision=0)
    db_session.add(board)
    await db_session.flush()

    bm = BoardMember(board_id=board.id, user_id=user.id, role="OWNER")
    db_session.add(bm)
    await db_session.commit()

    token = create_access_token(user.id)
    token_unauth = create_access_token(unauth_user.id)
    board_id = board.id

    # 2. Use Starlette TestClient in a separate thread/sync runner to test WebSockets
    def run_sync_ws_client():
        with TestClient(app) as client:
            # A. Missing token -> Rejected
            try:
                with client.websocket_connect(f"/ws/boards/{board_id}"):
                    assert False, "Should have failed with missing token"
            except Exception:
                pass

            # B. Unauthorized user -> Rejected
            try:
                with client.websocket_connect(f"/ws/boards/{board_id}?token={token_unauth}"):
                    assert False, "Should have failed for unauthorized user"
            except Exception:
                pass

            # C. Authorized user -> Connects and receives initial snapshot
            with client.websocket_connect(f"/ws/boards/{board_id}?token={token}") as ws_conn:
                snap = ws_conn.receive_json()
                assert snap["type"] == "SYNC_SNAPSHOT"
                assert snap["payload"]["role"] == "OWNER"

                # Send Cursor Movement
                ws_conn.send_json({
                    "type": "CURSOR_MOVED",
                    "board_id": board_id,
                    "payload": {"x": 120, "y": 240}
                })

                # Send Object Created
                ws_conn.send_json({
                    "type": "OBJECT_CREATED",
                    "operation_id": "op-ws-100",
                    "board_id": board_id,
                    "object_id": "sticky-100",
                    "payload": {
                        "id": "sticky-100",
                        "type": "sticky_note",
                        "x": 200,
                        "y": 200,
                        "text": "Hello WebSocket",
                    }
                })

                # Should receive broadcast event and ACK
                msgs = [ws_conn.receive_json(), ws_conn.receive_json()]
                types = [m["type"] for m in msgs]
                assert "OBJECT_CREATED" in types
                assert "ACK" in types

                # Send SYNC_REQUEST
                ws_conn.send_json({
                    "type": "SYNC_REQUEST",
                    "board_id": board_id
                })
                rec_snap = ws_conn.receive_json()
                assert rec_snap["type"] == "SYNC_SNAPSHOT"
                assert len(rec_snap["payload"]["objects"]) == 1

    await asyncio.to_thread(run_sync_ws_client)
