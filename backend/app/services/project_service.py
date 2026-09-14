from typing import List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.app.models.project import Project, ProjectMember
from backend.app.models.task import Task
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.schemas.project import ProjectCreate, ProjectUpdate
from backend.app.services.workspace_service import workspace_service


class ProjectService:
    @staticmethod
    async def check_project_access(
        db: AsyncSession, project_id: str, user_id: str
    ) -> Optional[str]:
        # 1. Direct ProjectMember check
        stmt = select(ProjectMember.role).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id
        )
        res = await db.execute(stmt)
        project_role = res.scalars().first()
        if project_role:
            return project_role

        # 2. Workspace role inheritance fallback
        stmt_ws = (
            select(WorkspaceMember.role)
            .join(Project, Project.workspace_id == WorkspaceMember.workspace_id)
            .where(Project.id == project_id, WorkspaceMember.user_id == user_id)
        )
        res_ws = await db.execute(stmt_ws)
        ws_role = res_ws.scalars().first()
        if ws_role in ["OWNER", "ADMIN"]:
            return "OWNER"
        elif ws_role == "MEMBER":
            return "MEMBER"
        return None

    @staticmethod
    async def create_project(
        db: AsyncSession, workspace_id: str, user_id: str, project_in: ProjectCreate
    ) -> Project:
        ws_role = await workspace_service.check_workspace_access(db, workspace_id, user_id)
        if not ws_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create projects in this workspace",
            )

        project = Project(
            workspace_id=workspace_id,
            name=project_in.name,
            description=project_in.description,
            revision=0,
        )
        db.add(project)
        await db.flush()
        await db.refresh(project)

        # Creator is project OWNER
        member = ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role="OWNER"
        )
        db.add(member)
        await db.flush()
        return project

    @staticmethod
    async def get_workspace_projects(
        db: AsyncSession, workspace_id: str, user_id: str
    ) -> List[dict]:
        ws_role = await workspace_service.check_workspace_access(db, workspace_id, user_id)
        if not ws_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access projects in this workspace",
            )

        stmt = (
            select(
                Project,
                func.count(Task.id).filter(Task.is_deleted.is_(False)).label("tasks_count")
            )
            .outerjoin(Task, Task.project_id == Project.id)
            .where(Project.workspace_id == workspace_id)
            .group_by(Project.id)
            .order_by(Project.updated_at.desc())
        )
        res = await db.execute(stmt)
        rows = res.all()

        results = []
        for project, count in rows:
            role = await ProjectService.check_project_access(db, project.id, user_id)
            results.append({
                "id": project.id,
                "workspace_id": project.workspace_id,
                "name": project.name,
                "description": project.description,
                "revision": project.revision,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "role": role or "MEMBER",
                "tasks_count": count or 0,
            })
        return results

    @staticmethod
    async def get_project(
        db: AsyncSession, project_id: str, user_id: str
    ) -> dict:
        role = await ProjectService.check_project_access(db, project_id, user_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this project",
            )

        stmt = select(Project).where(Project.id == project_id)
        res = await db.execute(stmt)
        project = res.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Count tasks
        cnt_stmt = select(func.count(Task.id)).where(
            Task.project_id == project_id,
            Task.is_deleted.is_(False)
        )
        count = (await db.execute(cnt_stmt)).scalar() or 0

        return {
            "id": project.id,
            "workspace_id": project.workspace_id,
            "name": project.name,
            "description": project.description,
            "revision": project.revision,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "role": role,
            "tasks_count": count,
        }

    @staticmethod
    async def update_project(
        db: AsyncSession, project_id: str, user_id: str, project_in: ProjectUpdate
    ) -> Project:
        role = await ProjectService.check_project_access(db, project_id, user_id)
        if role not in ["OWNER", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this project",
            )

        stmt = select(Project).where(Project.id == project_id)
        res = await db.execute(stmt)
        project = res.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if project_in.name is not None:
            project.name = project_in.name
        if project_in.description is not None:
            project.description = project_in.description
        await db.flush()
        await db.refresh(project)
        return project

    @staticmethod
    async def delete_project(
        db: AsyncSession, project_id: str, user_id: str
    ) -> None:
        role = await ProjectService.check_project_access(db, project_id, user_id)
        if role != "OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner can delete this project",
            )

        stmt = select(Project).where(Project.id == project_id)
        res = await db.execute(stmt)
        project = res.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.delete(project)
        await db.flush()

    @staticmethod
    async def add_project_member(
        db: AsyncSession, project_id: str, user_query: str, role: str, current_user_id: str
    ) -> ProjectMember:
        current_role = await ProjectService.check_project_access(db, project_id, current_user_id)
        if current_role not in ["OWNER", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner or admin can share and manage project members",
            )

        stmt = select(User).where(or_(User.email == user_query, User.username == user_query))
        res = await db.execute(stmt)
        target_user = res.scalars().first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found")

        stmt_mem = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == target_user.id
        )
        res_mem = await db.execute(stmt_mem)
        mem = res_mem.scalars().first()
        if mem:
            mem.role = role
        else:
            mem = ProjectMember(project_id=project_id, user_id=target_user.id, role=role)
            db.add(mem)
        await db.flush()
        await db.refresh(mem)
        return mem, target_user

    @staticmethod
    async def get_project_members(
        db: AsyncSession, project_id: str, user_id: str
    ) -> List[dict]:
        role = await ProjectService.check_project_access(db, project_id, user_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not authorized")

        stmt = (
            select(ProjectMember, User)
            .join(User, User.id == ProjectMember.user_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.created_at.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()
        return [
            {
                "id": pm.id,
                "project_id": pm.project_id,
                "user_id": pm.user_id,
                "role": pm.role,
                "username": u.username,
                "email": u.email,
                "created_at": pm.created_at,
            }
            for pm, u in rows
        ]

    @staticmethod
    async def remove_project_member(
        db: AsyncSession, project_id: str, member_user_id: str, current_user_id: str
    ) -> None:
        current_role = await ProjectService.check_project_access(db, project_id, current_user_id)
        if current_role not in ["OWNER", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the project owner or admin can remove members",
            )

        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_user_id,
        )
        res = await db.execute(stmt)
        pm = res.scalars().first()
        if not pm:
            raise HTTPException(status_code=404, detail="Project member not found")

        await db.delete(pm)
        await db.flush()

    @staticmethod
    async def get_project_snapshot(db: AsyncSession, project_id: str, user_id: str) -> dict:
        from fastapi import HTTPException
        role = await ProjectService.check_project_access(db, project_id, user_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not authorized")

        from backend.app.models.project import Project
        from backend.app.models.task import Task
        from backend.app.services.connection_manager import manager
        from sqlalchemy import select

        stmt = select(Project).where(Project.id == project_id)
        project = (await db.execute(stmt)).scalars().first()

        t_stmt = select(Task).where(Task.project_id == project_id, Task.is_deleted.is_(False))
        tasks = (await db.execute(t_stmt)).scalars().all()

        presence = await manager.get_room_presence(project_id)

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description,
            },
            "tasks": [t.to_dict() for t in tasks],
            "presence": presence,
            "role": role,
            "server_revision": project.revision,
        }


project_service = ProjectService()
