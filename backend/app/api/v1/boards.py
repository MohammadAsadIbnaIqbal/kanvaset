from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.board import (
    BoardCreate,
    BoardMemberAdd,
    BoardMemberOut,
    BoardOut,
    BoardUpdate,
)
from backend.app.services.board_service import board_service

router = APIRouter(tags=["Boards"])


@router.post("/workspaces/{workspace_id}/boards", response_model=BoardOut, status_code=status.HTTP_201_CREATED)
async def create_board(
    workspace_id: str,
    board_in: BoardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = await board_service.create_board(
        db, workspace_id=workspace_id, user_id=current_user.id, board_in=board_in
    )
    return BoardOut(
        id=board.id,
        workspace_id=board.workspace_id,
        name=board.name,
        description=board.description,
        revision=board.revision,
        created_by=board.created_by,
        created_at=board.created_at,
        updated_at=board.updated_at,
        role="OWNER",
        objects_count=0,
    )


@router.get("/workspaces/{workspace_id}/boards", response_model=List[BoardOut])
async def list_workspace_boards(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    boards = await board_service.get_workspace_boards(
        db, workspace_id=workspace_id, user_id=current_user.id
    )
    return [BoardOut(**b) for b in boards]


@router.get("/boards/{board_id}", response_model=BoardOut)
async def get_board(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board_dict = await board_service.get_board(
        db, board_id=board_id, user_id=current_user.id
    )
    return BoardOut(**board_dict)


@router.get("/boards/{board_id}/snapshot")
async def get_board_snapshot(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    snapshot = await board_service.get_board_snapshot(
        db, board_id=board_id, user_id=current_user.id
    )
    return snapshot


@router.patch("/boards/{board_id}", response_model=BoardOut)
async def update_board(
    board_id: str,
    board_in: BoardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    board = await board_service.update_board(
        db, board_id=board_id, user_id=current_user.id, board_in=board_in
    )
    role = await board_service.check_board_access(db, board.id, current_user.id)
    return BoardOut(
        id=board.id,
        workspace_id=board.workspace_id,
        name=board.name,
        description=board.description,
        revision=board.revision,
        created_by=board.created_by,
        created_at=board.created_at,
        updated_at=board.updated_at,
        role=role or "EDITOR",
    )


@router.delete("/boards/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await board_service.delete_board(
        db, board_id=board_id, user_id=current_user.id
    )
    return None


@router.post("/boards/{board_id}/members", response_model=BoardMemberOut)
async def add_board_member(
    board_id: str,
    member_in: BoardMemberAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member, target_user = await board_service.add_board_member(
        db=db,
        board_id=board_id,
        user_query=member_in.user_email_or_username,
        role=member_in.role,
        current_user_id=current_user.id,
    )
    return BoardMemberOut(
        id=member.id,
        board_id=member.board_id,
        user_id=member.user_id,
        role=member.role,
        username=target_user.username,
        email=target_user.email,
        avatar_url=target_user.avatar_url,
        created_at=member.created_at,
    )


@router.get("/boards/{board_id}/members", response_model=List[BoardMemberOut])
async def list_board_members(
    board_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    members = await board_service.get_board_members(
        db, board_id=board_id, user_id=current_user.id
    )
    return [BoardMemberOut(**m) for m in members]
