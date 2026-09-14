import pytest
from httpx import AsyncClient
from backend.app.main import app
from backend.app.models.project import Project, ProjectMember
from backend.app.models.task import Task
from backend.app.models.history import TaskVersion, Activity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

@pytest.mark.asyncio
async def test_project_crud(client: AsyncClient, auth_headers: dict, test_user: dict):
    ws_resp = await client.post(
        "/api/v1/workspaces",
        headers=auth_headers,
        json={"name": "Test WS for Project"}
    )
    assert ws_resp.status_code in (200, 201)
    ws_id = ws_resp.json()["id"]

    proj_resp = await client.post(
        f"/api/v1/projects/workspace/{ws_id}",
        headers=auth_headers,
        json={"workspace_id": ws_id, "name": "New Kanvaset Project", "description": "Desc"}
    )
    assert proj_resp.status_code in (200, 201)
    proj_data = proj_resp.json()
    assert proj_data["name"] == "New Kanvaset Project"
    proj_id = proj_data["id"]

    get_resp = await client.get(f"/api/v1/projects/{proj_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "New Kanvaset Project"

    patch_resp = await client.patch(
        f"/api/v1/projects/{proj_id}",
        headers=auth_headers,
        json={"name": "Updated Project"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated Project"


@pytest.mark.asyncio
async def test_task_crud_and_history(client: AsyncClient, auth_headers: dict, test_user: dict, db_session: AsyncSession):
    ws_resp = await client.post(
        "/api/v1/workspaces", headers=auth_headers, json={"name": "WS"}
    )
    ws_id = ws_resp.json()["id"]
    proj_resp = await client.post(
        f"/api/v1/projects/workspace/{ws_id}", headers=auth_headers, json={"workspace_id": ws_id, "name": "P"}
    )
    proj_id = proj_resp.json()["id"]

    task_resp = await client.post(
        f"/api/v1/tasks/project/{proj_id}",
        headers=auth_headers,
        json={
            "project_id": proj_id,
            "title": "Initial Task",
            "description": "Task desc"
        }
    )
    assert task_resp.status_code in (200, 201)
    task_data = task_resp.json()
    task_id = task_data["id"]
    assert task_data["title"] == "Initial Task"

    update_resp = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
        json={"status": "IN_PROGRESS", "title": "Updated Task"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "IN_PROGRESS"

    history_resp = await client.get(
        f"/api/v1/tasks/{task_id}/history",
        headers=auth_headers
    )
    assert history_resp.status_code == 200
    assert isinstance(history_resp.json(), list)

    comment_resp = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=auth_headers,
        json={"content": "This is a comment"}
    )
    assert comment_resp.status_code in (200, 201)
    assert comment_resp.json()["content"] == "This is a comment"

    comments_get = await client.get(
        f"/api/v1/tasks/{task_id}/comments",
        headers=auth_headers
    )
    assert comments_get.status_code == 200
    assert len(comments_get.json()) >= 1
