from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.app.models.board import Board
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember


class WorkspaceService:
    @staticmethod
    async def create_workspace(
        db: AsyncSession, user_id: str, name: str
    ) -> Workspace:
        workspace = Workspace(name=name, owner_id=user_id)
        db.add(workspace)
        await db.flush()
        await db.refresh(workspace)

        # Automatically add creator as OWNER member
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user_id,
            role="OWNER"
        )
        db.add(member)
        await db.flush()
        return workspace

    @staticmethod
    async def get_user_workspaces(
        db: AsyncSession, user_id: str
    ) -> List[dict]:
        # Workspaces where user is either owner or member
        stmt = (
            select(
                Workspace,
                WorkspaceMember.role,
                func.count(Board.id).label("boards_count")
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .outerjoin(Board, Board.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .group_by(Workspace.id, WorkspaceMember.role)
            .order_by(Workspace.created_at.desc())
        )
        res = await db.execute(stmt)
        rows = res.all()
        
        result = []
        for ws, role, boards_cnt in rows:
            result.append({
                "id": ws.id,
                "name": ws.name,
                "owner_id": ws.owner_id,
                "created_at": ws.created_at,
                "role": role,
                "boards_count": boards_cnt or 0,
            })
        return result

    @staticmethod
    async def check_workspace_access(
        db: AsyncSession, workspace_id: str, user_id: str
    ) -> Optional[str]:
        stmt = select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def get_workspace(
        db: AsyncSession, workspace_id: str, user_id: str
    ) -> dict:
        role = await WorkspaceService.check_workspace_access(db, workspace_id, user_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this workspace",
            )
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        res = await db.execute(stmt)
        ws = res.scalars().first()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return {
            "id": ws.id,
            "name": ws.name,
            "owner_id": ws.owner_id,
            "created_at": ws.created_at,
            "role": role
        }

    @staticmethod
    async def add_workspace_member(
        db: AsyncSession,
        workspace_id: str,
        user_query: str,
        role: str,
        current_user_id: str
    ) -> WorkspaceMember:
        current_role = await WorkspaceService.check_workspace_access(db, workspace_id, current_user_id)
        if current_role not in ["OWNER", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owners and admins can add members",
            )

        # Find target user
        stmt = select(User).where(or_(User.email == user_query, User.username == user_query))
        res = await db.execute(stmt)
        target_user = res.scalars().first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

        # Check existing membership
        stmt_mem = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id
        )
        res_mem = await db.execute(stmt_mem)
        mem = res_mem.scalars().first()
        if mem:
            mem.role = role
        else:
            mem = WorkspaceMember(workspace_id=workspace_id, user_id=target_user.id, role=role)
            db.add(mem)
        await db.flush()
        await db.refresh(mem)
        return mem, target_user


workspace_service = WorkspaceService()
