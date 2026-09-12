import asyncio
import json
import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient
from backend.app.core.database import async_session_maker
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.main import app
from backend.app.models.board import Board, BoardMember
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember


# ============================================================================
# REST API Error Boundary Tests
# ============================================================================

@pytest.mark.asyncio
async def test_api_missing_parameters_and_invalid_json(client: AsyncClient):
    """Test malformed JSON bodies and missing parameters on REST API."""
    # 1. Missing required fields in registration (missing username & password)
    resp = await client.post("/api/v1/auth/register", json={"email": "bad@example.com"})
    assert resp.status_code == 422

    # 2. Missing required fields in login (missing password)
    resp = await client.post("/api/v1/auth/login", json={"email": "bad@example.com"})
    assert resp.status_code == 422

    # 3. Invalid email format
    resp = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email",
        "username": "validname",
        "password": "validpassword123"
    })
    assert resp.status_code == 422

    # 4. Malformed raw JSON syntax
    resp = await client.post(
        "/api/v1/auth/register",
        content=b"{invalid_json_format",
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code in [400, 422]


@pytest.mark.asyncio
async def test_api_unauthenticated_access(client: AsyncClient, test_user: User):
    """Test unauthenticated or improperly authenticated access to protected endpoints."""
    # 1. Missing Authorization header
    resp = await client.get("/api/v1/workspaces")
    assert resp.status_code == 401
    assert "Authentication token required" in resp.json()["detail"]

    # 2. Malformed token (garbage bearer)
    resp = await client.get(
        "/api/v1/workspaces",
        headers={"Authorization": "Bearer garbage_token_value_xyz"}
    )
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]

    # 3. Token for non-existent user
    fake_token = create_access_token("00000000-0000-0000-0000-000000000000")
    resp = await client.get(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert resp.status_code == 401
    assert "User not found" in resp.json()["detail"]

    # 4. Protected board endpoints without auth
    resp = await client.get("/api/v1/boards/some-board-id")
    assert resp.status_code == 401

    resp = await client.get("/api/v1/boards/some-board-id/snapshot")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_workspace_and_board_authorization(
    client: AsyncClient,
    auth_headers: dict,
    auth_headers_b: dict,
    test_user: User,
    test_user_b: User,
):
    """Test cross-tenant authorization and RBAC boundaries."""
    # Alice creates a workspace and board
    ws_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Alice Private Workspace"},
        headers=auth_headers
    )
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    board_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/boards",
        json={"name": "Alice Secret Board"},
        headers=auth_headers
    )
    assert board_resp.status_code == 201
    board_id = board_resp.json()["id"]

    # Bob (unauthorized) tries to access Alice's workspace -> 403
    resp = await client.get(f"/api/v1/workspaces/{ws_id}", headers=auth_headers_b)
    assert resp.status_code == 403

    # Bob tries to list boards in Alice's workspace -> 403
    resp = await client.get(f"/api/v1/workspaces/{ws_id}/boards", headers=auth_headers_b)
    assert resp.status_code == 403

    # Bob tries to create a board in Alice's workspace -> 403
    resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/boards",
        json={"name": "Bob Infiltration Board"},
        headers=auth_headers_b
    )
    assert resp.status_code == 403

    # Bob tries to view Alice's board directly -> 403
    resp = await client.get(f"/api/v1/boards/{board_id}", headers=auth_headers_b)
    assert resp.status_code == 403

    # Bob tries to view Alice's board snapshot -> 403
    resp = await client.get(f"/api/v1/boards/{board_id}/snapshot", headers=auth_headers_b)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_viewer_mutation_boundaries(
    client: AsyncClient,
    auth_headers: dict,
    auth_headers_b: dict,
    test_user_b: User,
):
    """Test that VIEWER role is rejected from modifying board metadata or members."""
    # 1. Alice creates workspace and board
    ws_resp = await client.post("/api/v1/workspaces", json={"name": "Team WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    board_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/boards",
        json={"name": "Design Crit"},
        headers=auth_headers
    )
    board_id = board_resp.json()["id"]

    # 2. Alice adds Bob as VIEWER
    share_resp = await client.post(
        f"/api/v1/boards/{board_id}/members",
        json={"user_email_or_username": test_user_b.email, "role": "VIEWER"},
        headers=auth_headers
    )
    assert share_resp.status_code == 200

    # 3. Bob (VIEWER) attempts to rename board -> 403 Forbidden
    patch_resp = await client.patch(
        f"/api/v1/boards/{board_id}",
        json={"name": "Renamed By Viewer"},
        headers=auth_headers_b
    )
    assert patch_resp.status_code == 403
    assert "Not authorized to modify this board" in patch_resp.json()["detail"]

    # 4. Bob (VIEWER) attempts to delete board -> 403 Forbidden
    del_resp = await client.delete(f"/api/v1/boards/{board_id}", headers=auth_headers_b)
    assert del_resp.status_code == 403
    assert "Only the board owner can delete this board" in del_resp.json()["detail"]

    # 5. Bob (VIEWER) attempts to add new member -> 403 Forbidden
    add_mem_resp = await client.post(
        f"/api/v1/boards/{board_id}/members",
        json={"user_email_or_username": "charlie@example.com", "role": "EDITOR"},
        headers=auth_headers_b
    )
    assert add_mem_resp.status_code == 403
    assert "Only the board owner can share" in add_mem_resp.json()["detail"]


# ============================================================================
# WebSocket Error Boundary & Lifecycle Tests
# ============================================================================

@pytest.mark.asyncio
async def test_websocket_auth_and_access_rejections(db_session):
    """Test rejection of invalid WebSocket connections before upgrade."""
    user = User(
        email="ws_auth_test@example.com",
        username="ws_auth_test",
        hashed_password=get_password_hash("pass"),
    )
    user_unauth = User(
        email="ws_unauth_test@example.com",
        username="ws_unauth_test",
        hashed_password=get_password_hash("pass"),
    )
    db_session.add_all([user, user_unauth])
    await db_session.flush()

    ws = Workspace(name="WS Security", owner_id=user.id)
    db_session.add(ws)
    await db_session.flush()

    board = Board(workspace_id=ws.id, name="Secure Board", created_by=user.id, revision=0)
    db_session.add(board)
    await db_session.flush()

    bm = BoardMember(board_id=board.id, user_id=user.id, role="OWNER")
    db_session.add(bm)
    await db_session.commit()

    valid_token = create_access_token(user.id)
    unauth_token = create_access_token(user_unauth.id)
    board_id = board.id

    def run_tests():
        with TestClient(app) as client:
            # 1. No token at all
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/boards/{board_id}"):
                    pass

            # 2. Garbage token
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/boards/{board_id}?token=bad_token_123"):
                    pass

            # 3. User with valid token but not authorized for this board
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/boards/{board_id}?token={unauth_token}"):
                    pass

            # 4. Connecting to a non-existent board
            with pytest.raises(Exception):
                with client.websocket_connect(f"/ws/boards/non-existent-board-id?token={valid_token}"):
                    pass

    await asyncio.to_thread(run_tests)


@pytest.mark.asyncio
async def test_websocket_malformed_messages_and_viewer_mutations(db_session):
    """
    Test that malformed JSON, invalid schemas, and viewer mutations over WebSocket
    are gracefully handled with ERROR messages and DO NOT terminate the connection.
    """
    owner = User(
        email="board_owner@example.com",
        username="board_owner",
        hashed_password=get_password_hash("pass"),
    )
    viewer = User(
        email="board_viewer@example.com",
        username="board_viewer",
        hashed_password=get_password_hash("pass"),
    )
    db_session.add_all([owner, viewer])
    await db_session.flush()

    ws = Workspace(name="Collab WS", owner_id=owner.id)
    db_session.add(ws)
    await db_session.flush()

    board = Board(workspace_id=ws.id, name="Error Boundary Board", created_by=owner.id, revision=0)
    db_session.add(board)
    await db_session.flush()

    bm_owner = BoardMember(board_id=board.id, user_id=owner.id, role="OWNER")
    bm_viewer = BoardMember(board_id=board.id, user_id=viewer.id, role="VIEWER")
    db_session.add_all([bm_owner, bm_viewer])
    await db_session.commit()

    token_owner = create_access_token(owner.id)
    token_viewer = create_access_token(viewer.id)
    board_id = board.id

    def run_tests():
        with TestClient(app) as client:
            # -------------------------------------------------------------
            # Part 1: Malformed JSON and Schema Errors on an active socket
            # -------------------------------------------------------------
            with client.websocket_connect(f"/ws/boards/{board_id}?token={token_owner}") as ws_owner:
                # Consume initial snapshot
                snap = ws_owner.receive_json()
                assert snap["type"] == "SYNC_SNAPSHOT"

                # 1. Raw broken JSON string -> receives ERROR, connection remains alive!
                ws_owner.send_text("this is not valid json {{{")
                err1 = ws_owner.receive_json()
                assert err1["type"] == "ERROR"
                assert "Malformed WebSocket payload" in err1["payload"]["detail"]

                # 2. Valid JSON but missing required 'type' -> receives ERROR, connection remains alive!
                ws_owner.send_json({"board_id": board_id, "foo": "bar"})
                err2 = ws_owner.receive_json()
                assert err2["type"] == "ERROR"
                assert "Malformed WebSocket payload" in err2["payload"]["detail"]

                # 3. Unknown / invalid message type -> receives ERROR, connection remains alive!
                ws_owner.send_json({"type": "TOTALLY_INVALID_TYPE", "board_id": board_id})
                err3 = ws_owner.receive_json()
                assert err3["type"] == "ERROR"
                assert "Malformed WebSocket payload" in err3["payload"]["detail"]

                # 4. Mutation on non-existent object
                ws_owner.send_json({
                    "type": "OBJECT_MOVED",
                    "operation_id": "op-nonexistent-1",
                    "board_id": board_id,
                    "object_id": "non_existent_obj_123",
                    "payload": {"x": 100, "y": 200}
                })
                err4 = ws_owner.receive_json()
                assert err4["type"] == "ERROR"
                assert "not found" in err4["payload"]["detail"]

                # 5. Socket is still fully functional: cursor move works
                ws_owner.send_json({
                    "type": "CURSOR_MOVED",
                    "board_id": board_id,
                    "payload": {"x": 50, "y": 50}
                })

            # -------------------------------------------------------------
            # Part 2: Viewer attempting mutations over WebSocket
            # -------------------------------------------------------------
            with client.websocket_connect(f"/ws/boards/{board_id}?token={token_viewer}") as ws_v:
                snap_v = ws_v.receive_json()
                assert snap_v["type"] == "SYNC_SNAPSHOT"
                assert snap_v["payload"]["role"] == "VIEWER"

                # Viewer sends OBJECT_CREATED -> Rejected with ERROR
                ws_v.send_json({
                    "type": "OBJECT_CREATED",
                    "operation_id": "op-viewer-create",
                    "board_id": board_id,
                    "object_id": "sticky-viewer-1",
                    "payload": {"id": "sticky-viewer-1", "type": "sticky_note"}
                })
                err_v1 = ws_v.receive_json()
                assert err_v1["type"] == "ERROR"
                assert "Viewers are not permitted to modify this board" in err_v1["payload"]["detail"]

                # Viewer sends OBJECT_MOVED -> Rejected with ERROR
                ws_v.send_json({
                    "type": "OBJECT_MOVED",
                    "operation_id": "op-viewer-move",
                    "board_id": board_id,
                    "object_id": "sticky-viewer-1",
                    "payload": {"x": 200, "y": 200}
                })
                err_v2 = ws_v.receive_json()
                assert err_v2["type"] == "ERROR"
                assert "Viewers are not permitted to modify this board" in err_v2["payload"]["detail"]

                # Viewer sends OBJECT_DELETED -> Rejected with ERROR
                ws_v.send_json({
                    "type": "OBJECT_DELETED",
                    "operation_id": "op-viewer-delete",
                    "board_id": board_id,
                    "object_id": "sticky-viewer-1",
                })
                err_v3 = ws_v.receive_json()
                assert err_v3["type"] == "ERROR"
                assert "Viewers are not permitted to modify this board" in err_v3["payload"]["detail"]

                # Viewer can still request SYNC_SNAPSHOT
                ws_v.send_json({
                    "type": "SYNC_REQUEST",
                    "board_id": board_id
                })
                sync_snap = ws_v.receive_json()
                assert sync_snap["type"] == "SYNC_SNAPSHOT"
                assert sync_snap["payload"]["role"] == "VIEWER"

            # -------------------------------------------------------------
            # Part 3: Malformed numeric values in payload (must not crash socket)
            # -------------------------------------------------------------
            with client.websocket_connect(f"/ws/boards/{board_id}?token={token_owner}") as ws_owner:
                ws_owner.receive_json()  # snapshot

                # 1. Create a valid object first
                ws_owner.send_json({
                    "type": "OBJECT_CREATED",
                    "operation_id": "op-valid-1",
                    "board_id": board_id,
                    "object_id": "sticky-num-test",
                    "payload": {
                        "id": "sticky-num-test",
                        "type": "sticky_note",
                        "x": 100,
                        "y": 100,
                    }
                })
                # Receive broadcast and ack
                _ = ws_owner.receive_json()
                _ = ws_owner.receive_json()

                # 2. Send OBJECT_MOVED with non-numeric coordinates (e.g. x='invalid')
                ws_owner.send_json({
                    "type": "OBJECT_MOVED",
                    "operation_id": "op-bad-coords",
                    "board_id": board_id,
                    "object_id": "sticky-num-test",
                    "payload": {"x": "not_a_float", "y": 200}
                })
                # Should receive ERROR response, NOT crash connection!
                err_num = ws_owner.receive_json()
                assert err_num["type"] == "ERROR"

                # 3. Connection is still healthy and accepts subsequent valid moves
                ws_owner.send_json({
                    "type": "OBJECT_MOVED",
                    "operation_id": "op-good-move",
                    "board_id": board_id,
                    "object_id": "sticky-num-test",
                    "payload": {"x": 300, "y": 300}
                })
                resp = ws_owner.receive_json()
                assert resp["type"] in ["OBJECT_MOVED", "ACK"]

    await asyncio.to_thread(run_tests)


@pytest.mark.asyncio
async def test_cross_board_object_isolation_and_ghost_deletes(db_session, test_user: User):
    """Verify that objects cannot be hijacked across boards and ghost deletes are rejected."""
    ws = Workspace(name="Isolation WS", owner_id=test_user.id)
    db_session.add(ws)
    await db_session.flush()

    board1 = Board(workspace_id=ws.id, name="Board 1", created_by=test_user.id, revision=0)
    board2 = Board(workspace_id=ws.id, name="Board 2", created_by=test_user.id, revision=0)
    db_session.add_all([board1, board2])
    await db_session.flush()

    bm1 = BoardMember(board_id=board1.id, user_id=test_user.id, role="OWNER")
    bm2 = BoardMember(board_id=board2.id, user_id=test_user.id, role="OWNER")
    db_session.add_all([bm1, bm2])
    await db_session.commit()

    token = create_access_token(test_user.id)

    def run_tests():
        with TestClient(app) as client:
            # 1. Create object on Board 1
            with client.websocket_connect(f"/ws/boards/{board1.id}?token={token}") as ws1:
                ws1.receive_json()  # snapshot
                ws1.send_json({
                    "type": "OBJECT_CREATED",
                    "operation_id": "op-b1-create",
                    "board_id": board1.id,
                    "object_id": "unique-obj-123",
                    "payload": {"id": "unique-obj-123", "type": "circle", "x": 10, "y": 10}
                })
                _ = ws1.receive_json()
                _ = ws1.receive_json()

            # 2. Attempt to create the same object ID on Board 2 -> Must be rejected!
            with client.websocket_connect(f"/ws/boards/{board2.id}?token={token}") as ws2:
                ws2.receive_json()  # snapshot
                ws2.send_json({
                    "type": "OBJECT_CREATED",
                    "operation_id": "op-b2-conflict",
                    "board_id": board2.id,
                    "object_id": "unique-obj-123",
                    "payload": {"id": "unique-obj-123", "type": "rectangle", "x": 99, "y": 99}
                })
                err_conflict = ws2.receive_json()
                assert err_conflict["type"] == "ERROR"
                assert "belongs to another board" in err_conflict["payload"]["detail"]

            # 3. Test ghost delete rejection on Board 1
            with client.websocket_connect(f"/ws/boards/{board1.id}?token={token}") as ws1:
                ws1.receive_json()

                # Ghost delete on non-existent object
                ws1.send_json({
                    "type": "OBJECT_DELETED",
                    "operation_id": "op-del-ghost",
                    "board_id": board1.id,
                    "object_id": "never-existed-obj",
                })
                err_ghost = ws1.receive_json()
                assert err_ghost["type"] == "ERROR"
                assert "not found" in err_ghost["payload"]["detail"]

                # Valid delete
                ws1.send_json({
                    "type": "OBJECT_DELETED",
                    "operation_id": "op-del-real",
                    "board_id": board1.id,
                    "object_id": "unique-obj-123",
                })
                # Receive broadcast and ack
                msgs = [ws1.receive_json(), ws1.receive_json()]
                assert any(m["type"] == "OBJECT_DELETED" for m in msgs)

                # Duplicate delete on now-deleted object
                ws1.send_json({
                    "type": "OBJECT_DELETED",
                    "operation_id": "op-del-again",
                    "board_id": board1.id,
                    "object_id": "unique-obj-123",
                })
                err_dup_del = ws1.receive_json()
                assert err_dup_del["type"] == "ERROR"
                assert "not found" in err_dup_del["payload"]["detail"]

    await asyncio.to_thread(run_tests)


@pytest.mark.asyncio
async def test_multi_client_concurrent_collaboration_and_reconnect(
    db_session, test_user: User, test_user_b: User
):
    """
    Test real-time WebSocket multi-user concurrent edits,
    cursor streaming, disconnect, and reconnect state recovery.
    """
    ws = Workspace(name="Live Collab WS", owner_id=test_user.id)
    db_session.add(ws)
    await db_session.flush()

    board = Board(workspace_id=ws.id, name="Live Room", created_by=test_user.id, revision=0)
    db_session.add(board)
    await db_session.flush()

    bm_owner = BoardMember(board_id=board.id, user_id=test_user.id, role="OWNER")
    bm_editor = BoardMember(board_id=board.id, user_id=test_user_b.id, role="EDITOR")
    db_session.add_all([bm_owner, bm_editor])
    await db_session.commit()

    token_a = create_access_token(test_user.id)
    token_b = create_access_token(test_user_b.id)
    board_id = board.id

    def run_tests():
        with TestClient(app) as client:
            with client.websocket_connect(f"/ws/boards/{board_id}?token={token_a}") as ws_a:
                snap_a = ws_a.receive_json()
                assert snap_a["type"] == "SYNC_SNAPSHOT"
                assert snap_a["payload"]["role"] == "OWNER"

                # Bob connects concurrently
                with client.websocket_connect(f"/ws/boards/{board_id}?token={token_b}") as ws_b:
                    snap_b = ws_b.receive_json()
                    assert snap_b["type"] == "SYNC_SNAPSHOT"
                    assert snap_b["payload"]["role"] == "EDITOR"

                    # Alice receives Bob's USER_JOINED
                    msg_for_a = ws_a.receive_json()
                    assert msg_for_a["type"] == "USER_JOINED"
                    assert msg_for_a["payload"]["user"]["username"] == test_user_b.username

                    # Alice streams cursor position
                    ws_a.send_json({
                        "type": "CURSOR_MOVED",
                        "board_id": board_id,
                        "payload": {"x": 250, "y": 350}
                    })
                    # Bob receives Alice's cursor
                    cursor_b = ws_b.receive_json()
                    assert cursor_b["type"] == "CURSOR_MOVED"
                    assert cursor_b["payload"]["x"] == 250
                    assert cursor_b["payload"]["y"] == 350
                    assert cursor_b["payload"]["user_name"] == test_user.username

                    # Bob creates a sticky note
                    ws_b.send_json({
                        "type": "OBJECT_CREATED",
                        "operation_id": "op-collab-sticky",
                        "board_id": board_id,
                        "object_id": "sticky-collab-1",
                        "payload": {
                            "id": "sticky-collab-1",
                            "type": "sticky_note",
                            "x": 100,
                            "y": 100,
                            "text": "Concurrent Note"
                        }
                    })

                    # Both clients receive broadcasts
                    msg_a = ws_a.receive_json()
                    assert msg_a["type"] == "OBJECT_CREATED"
                    assert msg_a["payload"]["text"] == "Concurrent Note"

                    # Bob consumes broadcast and ACK
                    b_msgs = [ws_b.receive_json(), ws_b.receive_json()]
                    assert any(m["type"] == "OBJECT_CREATED" for m in b_msgs)
                    assert any(m["type"] == "ACK" for m in b_msgs)

                    # Alice moves Bob's sticky note
                    ws_a.send_json({
                        "type": "OBJECT_MOVED",
                        "operation_id": "op-collab-move",
                        "board_id": board_id,
                        "object_id": "sticky-collab-1",
                        "payload": {"x": 500, "y": 600}
                    })

                    # Bob receives Alice's move
                    b_move = ws_b.receive_json()
                    assert b_move["type"] == "OBJECT_MOVED"
                    assert b_move["payload"]["x"] == 500
                    assert b_move["payload"]["y"] == 600

                    # Alice consumes ACK and broadcast
                    a_msgs = [ws_a.receive_json(), ws_a.receive_json()]
                    assert any(m["type"] == "OBJECT_MOVED" for m in a_msgs)
                    assert any(m["type"] == "ACK" for m in a_msgs)

                # Bob has disconnected! Alice receives Bob's USER_LEFT
                left_msg = ws_a.receive_json()
                assert left_msg["type"] == "USER_LEFT"
                assert left_msg["payload"]["user_id"] == test_user_b.id

                # Now Bob reconnects to the board
                with client.websocket_connect(f"/ws/boards/{board_id}?token={token_b}") as ws_b_reconnected:
                    recon_snap = ws_b_reconnected.receive_json()
                    assert recon_snap["type"] == "SYNC_SNAPSHOT"
                    assert len(recon_snap["payload"]["objects"]) == 1
                    persisted = recon_snap["payload"]["objects"][0]
                    assert persisted["id"] == "sticky-collab-1"
                    assert persisted["x"] == 500
                    assert persisted["y"] == 600
                    assert persisted["text"] == "Concurrent Note"

    await asyncio.to_thread(run_tests)

