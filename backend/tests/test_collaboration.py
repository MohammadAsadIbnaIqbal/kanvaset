import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.board import Board, BoardMember
from backend.app.models.workspace import Workspace
from backend.app.schemas.ws_messages import WSMessage, WSMessageType
from backend.app.services.board_service import board_service
from backend.app.services.collaboration_engine import collaboration_engine


@pytest.mark.asyncio
async def test_collaboration_operations_and_concurrency(
    db_session: AsyncSession, test_user, test_user_b
):
    # Setup test workspace and board
    ws = Workspace(name="Test WS", owner_id=test_user.id)
    db_session.add(ws)
    await db_session.flush()

    board = Board(workspace_id=ws.id, name="Realtime Board", created_by=test_user.id, revision=0)
    db_session.add(board)
    await db_session.flush()

    bm_owner = BoardMember(board_id=board.id, user_id=test_user.id, role="OWNER")
    bm_viewer = BoardMember(board_id=board.id, user_id=test_user_b.id, role="VIEWER")
    db_session.add_all([bm_owner, bm_viewer])
    await db_session.commit()

    # 1. OBJECT_CREATED by Owner
    op_create = WSMessage(
        type=WSMessageType.OBJECT_CREATED,
        operation_id="op-1",
        board_id=board.id,
        object_id="sticky-1",
        payload={
            "id": "sticky-1",
            "type": "sticky_note",
            "x": 100.0,
            "y": 150.0,
            "width": 200.0,
            "height": 200.0,
            "text": "Brainstorming idea #1",
            "color": "#FEF08A",
        },
    )
    bcast_msg, err = await collaboration_engine.process_operation(
        db=db_session,
        msg=op_create,
        user_id=test_user.id,
        user_name=test_user.username,
        role="OWNER",
    )
    assert err is None
    assert bcast_msg is not None
    assert bcast_msg.server_revision == 1
    assert bcast_msg.payload["version"] == 1
    assert bcast_msg.payload["text"] == "Brainstorming idea #1"
    await db_session.commit()

    # 2. OBJECT_MOVED by Owner
    op_move = WSMessage(
        type=WSMessageType.OBJECT_MOVED,
        operation_id="op-2",
        board_id=board.id,
        object_id="sticky-1",
        payload={"x": 250.0, "y": 300.0},
    )
    bcast_msg, err = await collaboration_engine.process_operation(
        db=db_session,
        msg=op_move,
        user_id=test_user.id,
        user_name=test_user.username,
        role="OWNER",
    )
    assert err is None
    assert bcast_msg.server_revision == 2
    assert bcast_msg.payload["version"] == 2
    assert bcast_msg.payload["x"] == 250.0
    await db_session.commit()

    # 3. Viewer attempts to modify -> REJECTED
    op_viewer_edit = WSMessage(
        type=WSMessageType.OBJECT_UPDATED,
        operation_id="op-viewer-illegal",
        board_id=board.id,
        object_id="sticky-1",
        payload={"text": "Viewer unauthorized change"},
    )
    bcast_msg, err = await collaboration_engine.process_operation(
        db=db_session,
        msg=op_viewer_edit,
        user_id=test_user_b.id,
        user_name=test_user_b.username,
        role="VIEWER",
    )
    assert err is not None
    assert "Viewers are not permitted" in err
    assert bcast_msg is None

    # 4. Operation Deduplication: Replaying op-2 returns ACK with current revision without re-applying
    dup_msg, err = await collaboration_engine.process_operation(
        db=db_session,
        msg=op_move,
        user_id=test_user.id,
        user_name=test_user.username,
        role="OWNER",
    )
    assert err is None
    assert dup_msg is not None
    assert dup_msg.type == WSMessageType.ACK
    assert dup_msg.server_revision == 2

    # 5. Snapshot validation
    snapshot = await board_service.get_board_snapshot(db_session, board.id, test_user.id)
    assert snapshot["server_revision"] == 2
    assert len(snapshot["objects"]) == 1
    assert snapshot["objects"][0]["x"] == 250.0
    assert snapshot["objects"][0]["version"] == 2

    # 6. OBJECT_DELETED
    op_delete = WSMessage(
        type=WSMessageType.OBJECT_DELETED,
        operation_id="op-3",
        board_id=board.id,
        object_id="sticky-1",
    )
    bcast_msg, err = await collaboration_engine.process_operation(
        db=db_session,
        msg=op_delete,
        user_id=test_user.id,
        user_name=test_user.username,
        role="OWNER",
    )
    assert err is None
    assert bcast_msg.server_revision == 3
    await db_session.commit()

    # Verify object is soft-deleted and omitted from active snapshot
    new_snapshot = await board_service.get_board_snapshot(db_session, board.id, test_user.id)
    assert len(new_snapshot["objects"]) == 0
