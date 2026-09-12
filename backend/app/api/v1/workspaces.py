from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceMemberOut,
    WorkspaceOut,
)
from backend.app.services.workspace_service import workspace_service

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await workspace_service.create_workspace(
        db, user_id=current_user.id, name=workspace_in.name
    )
    return WorkspaceOut(
        id=ws.id,
        name=ws.name,
        owner_id=ws.owner_id,
        created_at=ws.created_at,
        role="OWNER",
        boards_count=0,
    )


@router.get("", response_model=List[WorkspaceOut])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspaces = await workspace_service.get_user_workspaces(db, user_id=current_user.id)
    return [WorkspaceOut(**ws) for ws in workspaces]


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_dict = await workspace_service.get_workspace(
        db, workspace_id=workspace_id, user_id=current_user.id
    )
    return WorkspaceOut(**ws_dict)


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberOut)
async def add_workspace_member(
    workspace_id: str,
    member_in: WorkspaceMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member, target_user = await workspace_service.add_workspace_member(
        db=db,
        workspace_id=workspace_id,
        user_query=member_in.user_email_or_username,
        role=member_in.role,
        current_user_id=current_user.id,
    )
    return WorkspaceMemberOut(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        username=target_user.username,
        email=target_user.email,
        role=member.role,
        created_at=member.created_at,
    )
