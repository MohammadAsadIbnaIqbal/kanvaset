from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.app.core.redis import redis_service
from backend.app.models.board import Board, BoardMember
from backend.app.models.board_object import BoardObject
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.schemas.board import BoardCreate, BoardUpdate
from backend.app.services.workspace_service import workspace_service


class BoardService:
    @staticmethod
    async def check_board_access(
        db: AsyncSession, board_id: str, user_id: str
    ) -> Optional[str]:
        # 1. Direct BoardMember check
        stmt = select(BoardMember.role).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == user_id
        )
        res = await db.execute(stmt)
        board_role = res.scalars().first()
        if board_role:
            return board_role

        # 2. Workspace role inheritance fallback
        stmt_ws = (
            select(WorkspaceMember.role)
            .join(Board, Board.workspace_id == WorkspaceMember.workspace_id)
            .where(Board.id == board_id, WorkspaceMember.user_id == user_id)
        )
        res_ws = await db.execute(stmt_ws)
        ws_role = res_ws.scalars().first()
        if ws_role in ["OWNER", "ADMIN"]:
            return "OWNER"
        elif ws_role == "MEMBER":
            return "EDITOR"
        return None

    @staticmethod
    async def create_board(
        db: AsyncSession, workspace_id: str, user_id: str, board_in: BoardCreate
    ) -> Board:
        ws_role = await workspace_service.check_workspace_access(db, workspace_id, user_id)
        if not ws_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create boards in this workspace",
            )

        board = Board(
            workspace_id=workspace_id,
            name=board_in.name,
            description=board_in.description,
            created_by=user_id,
            revision=0,
        )
        db.add(board)
        await db.flush()
        await db.refresh(board)

        # Creator is board OWNER
        member = BoardMember(
            board_id=board.id,
            user_id=user_id,
            role="OWNER"
        )
        db.add(member)
        await db.flush()
        return board

    @staticmethod
    async def get_workspace_boards(
        db: AsyncSession, workspace_id: str, user_id: str
    ) -> List[dict]:
        ws_role = await workspace_service.check_workspace_access(db, workspace_id, user_id)
        if not ws_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access boards in this workspace",
            )

        stmt = (
            select(
                Board,
                func.count(BoardObject.id).filter(BoardObject.is_deleted.is_(False)).label("objects_count")
            )
            .outerjoin(BoardObject, BoardObject.board_id == Board.id)
            .where(Board.workspace_id == workspace_id)
            .group_by(Board.id)
            .order_by(Board.updated_at.desc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for board, count in rows:
            role = await BoardService.check_board_access(db, board.id, user_id)
            results.append({
                "id": board.id,
                "workspace_id": board.workspace_id,
                "name": board.name,
                "description": board.description,
                "revision": board.revision,
                "created_by": board.created_by,
                "created_at": board.created_at,
                "updated_at": board.updated_at,
                "role": role or "EDITOR",
                "objects_count": count or 0,
            })
        return results

    @staticmethod
    async def get_board(
        db: AsyncSession, board_id: str, user_id: str
    ) -> dict:
        role = await BoardService.check_board_access(db, board_id, user_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this board",
            )

        stmt = select(Board).where(Board.id == board_id)
        res = await db.execute(stmt)
        board = res.scalars().first()
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")

        # Count objects
        cnt_stmt = select(func.count(BoardObject.id)).where(
            BoardObject.board_id == board_id,
            BoardObject.is_deleted.is_(False)
        )
        count = (await db.execute(cnt_stmt)).scalar() or 0

        return {
            "id": board.id,
            "workspace_id": board.workspace_id,
            "name": board.name,
            "description": board.description,
            "revision": board.revision,
            "created_by": board.created_by,
            "created_at": board.created_at,
            "updated_at": board.updated_at,
            "role": role,
            "objects_count": count,
        }

    @staticmethod
    async def update_board(
        db: AsyncSession, board_id: str, user_id: str, board_in: BoardUpdate
    ) -> Board:
        role = await BoardService.check_board_access(db, board_id, user_id)
        if role not in ["OWNER", "EDITOR"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this board",
            )

        stmt = select(Board).where(Board.id == board_id)
        res = await db.execute(stmt)
        board = res.scalars().first()
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")

        if board_in.name is not None:
            board.name = board_in.name
        if board_in.description is not None:
            board.description = board_in.description
        await db.flush()
        await db.refresh(board)
        return board

    @staticmethod
    async def delete_board(
        db: AsyncSession, board_id: str, user_id: str
    ) -> None:
        role = await BoardService.check_board_access(db, board_id, user_id)
        if role != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the board owner can delete this board",
            )

        stmt = select(Board).where(Board.id == board_id)
        res = await db.execute(stmt)
        board = res.scalars().first()
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")

        await db.delete(board)
        await db.flush()

    @staticmethod
    async def add_board_member(
        db: AsyncSession, board_id: str, user_query: str, role: str, current_user_id: str
    ) -> BoardMember:
        current_role = await BoardService.check_board_access(db, board_id, current_user_id)
        if current_role != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the board owner can share and manage board members",
            )

        stmt = select(User).where(or_(User.email == user_query, User.username == user_query))
        res = await db.execute(stmt)
        target_user = res.scalars().first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

        stmt_mem = select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == target_user.id
        )
        res_mem = await db.execute(stmt_mem)
        mem = res_mem.scalars().first()
        if mem:
            mem.role = role
        else:
            mem = BoardMember(board_id=board_id, user_id=target_user.id, role=role)
            db.add(mem)
        await db.flush()
        await db.refresh(mem)
        return mem, target_user

    @staticmethod
    async def get_board_members(
        db: AsyncSession, board_id: str, user_id: str
    ) -> List[dict]:
        role = await BoardService.check_board_access(db, board_id, user_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not authorized")

        stmt = (
            select(BoardMember, User)
            .join(User, User.id == BoardMember.user_id)
            .where(BoardMember.board_id == board_id)
            .order_by(BoardMember.created_at.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()
        return [
            {
                "id": bm.id,
                "board_id": bm.board_id,
                "user_id": bm.user_id,
                "role": bm.role,
                "username": u.username,
                "email": u.email,
                "avatar_url": u.avatar_url,
                "created_at": bm.created_at,
            }
            for bm, u in rows
        ]

    @staticmethod
    async def update_board_member(
        db: AsyncSession, board_id: str, member_user_id: str, role: str, current_user_id: str
    ):
        current_role = await BoardService.check_board_access(db, board_id, current_user_id)
        if current_role != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the board owner can update member roles",
            )

        stmt = select(BoardMember, User).join(User, User.id == BoardMember.user_id).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == member_user_id,
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Board member not found")

        bm, target_user = row
        bm.role = role
        await db.flush()
        await db.refresh(bm)
        return bm, target_user

    @staticmethod
    async def remove_board_member(
        db: AsyncSession, board_id: str, member_user_id: str, current_user_id: str
    ) -> None:
        current_role = await BoardService.check_board_access(db, board_id, current_user_id)
        if current_role != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the board owner can remove members",
            )

        stmt = select(BoardMember).where(
            BoardMember.board_id == board_id,
            BoardMember.user_id == member_user_id,
        )
        res = await db.execute(stmt)
        bm = res.scalars().first()
        if not bm:
            raise HTTPException(status_code=404, detail="Board member not found")

        await db.delete(bm)
        await db.flush()

    @staticmethod
    async def get_board_snapshot(
        db: AsyncSession, board_id: str, user_id: Optional[str] = None
    ) -> dict:
        stmt = select(Board).where(Board.id == board_id)
        res = await db.execute(stmt)
        board = res.scalars().first()
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")

        # Fetch active objects
        obj_stmt = (
            select(BoardObject)
            .where(BoardObject.board_id == board_id, BoardObject.is_deleted.is_(False))
            .order_by(BoardObject.z_index.asc())
        )
        res_obj = await db.execute(obj_stmt)
        objects = [obj.to_dict() for obj in res_obj.scalars().all()]

        # Active presence
        presence = await redis_service.get_presence(board_id)

        # User role
        role = "EDITOR"
        if user_id:
            role = await BoardService.check_board_access(db, board_id, user_id)
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this board",
                )

        return {
            "board": {
                "id": board.id,
                "workspace_id": board.workspace_id,
                "name": board.name,
                "description": board.description,
                "revision": board.revision,
                "created_by": board.created_by,
                "created_at": board.created_at.isoformat() if board.created_at else None,
                "updated_at": board.updated_at.isoformat() if board.updated_at else None,
            },
            "objects": objects,
            "presence": presence,
            "role": role,
            "server_revision": board.revision,
        }


board_service = BoardService()
