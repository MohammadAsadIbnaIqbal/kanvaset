import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workspaces_and_boards_flow(
    client: AsyncClient,
    auth_headers: dict,
    auth_headers_b: dict,
    test_user,
    test_user_b,
):
    # 1. Create Workspace
    ws_resp = await client.post(
        "/api/v1/workspaces",
        json={"name": "Engineering Team"},
        headers=auth_headers,
    )
    assert ws_resp.status_code == 201
    ws_data = ws_resp.json()
    ws_id = ws_data["id"]
    assert ws_data["name"] == "Engineering Team"
    assert ws_data["role"] == "OWNER"

    # 2. List Workspaces
    list_ws = await client.get("/api/v1/workspaces", headers=auth_headers)
    assert list_ws.status_code == 200
    assert len(list_ws.json()) >= 1

    # 3. Create Board
    board_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/boards",
        json={"name": "Sprint 42 Retrospective", "description": "Whiteboard for retro"},
        headers=auth_headers,
    )
    assert board_resp.status_code == 201
    board_data = board_resp.json()
    board_id = board_data["id"]
    assert board_data["name"] == "Sprint 42 Retrospective"
    assert board_data["revision"] == 0
    assert board_data["role"] == "OWNER"

    # 4. User B cannot access board yet
    unauth_board = await client.get(
        f"/api/v1/boards/{board_id}",
        headers=auth_headers_b,
    )
    assert unauth_board.status_code == 403

    # 5. Share board with User B as VIEWER
    share_resp = await client.post(
        f"/api/v1/boards/{board_id}/members",
        json={"user_email_or_username": test_user_b.email, "role": "VIEWER"},
        headers=auth_headers,
    )
    assert share_resp.status_code == 200
    assert share_resp.json()["role"] == "VIEWER"

    # 6. Now User B can view the board with role VIEWER
    b_view = await client.get(
        f"/api/v1/boards/{board_id}",
        headers=auth_headers_b,
    )
    assert b_view.status_code == 200
    assert b_view.json()["role"] == "VIEWER"

    # 7. User B cannot update board metadata (only OWNER/EDITOR can)
    b_update = await client.patch(
        f"/api/v1/boards/{board_id}",
        json={"name": "Hacked Title"},
        headers=auth_headers_b,
    )
    assert b_update.status_code == 403

    # 8. Owner updates board title
    owner_update = await client.patch(
        f"/api/v1/boards/{board_id}",
        json={"name": "Q3 Planning & Retro"},
        headers=auth_headers,
    )
    assert owner_update.status_code == 200
    assert owner_update.json()["name"] == "Q3 Planning & Retro"

    # 9. Snapshot endpoint
    snapshot_resp = await client.get(
        f"/api/v1/boards/{board_id}/snapshot",
        headers=auth_headers,
    )
    assert snapshot_resp.status_code == 200
    snap = snapshot_resp.json()
    assert snap["board"]["name"] == "Q3 Planning & Retro"
    assert "objects" in snap
    assert "presence" in snap
