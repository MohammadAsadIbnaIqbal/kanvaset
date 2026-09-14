from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from backend.app.models.task import Task, TaskComment
from backend.app.models.user import User
from backend.app.schemas.task import TaskCreate, TaskUpdate, TaskCommentCreate
from backend.app.services.project_service import project_service


class TaskService:
    @staticmethod
    async def create_task(
        db: AsyncSession, project_id: str, user_id: str, task_in: TaskCreate
    ) -> Task:
        role = await project_service.check_project_access(db, project_id, user_id)
        if role not in ["OWNER", "ADMIN", "MEMBER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create tasks in this project",
            )

        task = Task(
            project_id=project_id,
            title=task_in.title,
            description=task_in.description,
            status=task_in.status,
            priority=task_in.priority,
            assignee_id=task_in.assignee_id,
            due_date=task_in.due_date,
            tags=task_in.tags,
            created_by=user_id,
            last_modified_by=user_id,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_project_tasks(
        db: AsyncSession, project_id: str, user_id: str
    ) -> List[Task]:
        role = await project_service.check_project_access(db, project_id, user_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access tasks in this project",
            )

        stmt = select(Task).where(
            Task.project_id == project_id,
            Task.is_deleted.is_(False)
        ).order_by(Task.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_task(
        db: AsyncSession, task_id: str, user_id: str
    ) -> Task:
        stmt = select(Task).where(Task.id == task_id, Task.is_deleted.is_(False))
        res = await db.execute(stmt)
        task = res.scalars().first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        role = await project_service.check_project_access(db, task.project_id, user_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this task",
            )

        return task

    @staticmethod
    async def update_task(
        db: AsyncSession, task_id: str, user_id: str, task_in: TaskUpdate
    ) -> Task:
        task = await TaskService.get_task(db, task_id, user_id)
        role = await project_service.check_project_access(db, task.project_id, user_id)
        if role not in ["OWNER", "ADMIN", "MEMBER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update tasks in this project",
            )

        update_data = task_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)
        
        task.last_modified_by = user_id
        task.version += 1
        
        await db.flush()
        await db.refresh(task)
        return task

    @staticmethod
    async def delete_task(
        db: AsyncSession, task_id: str, user_id: str
    ) -> None:
        task = await TaskService.get_task(db, task_id, user_id)
        role = await project_service.check_project_access(db, task.project_id, user_id)
        if role not in ["OWNER", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only project owners and admins can delete tasks",
            )

        task.is_deleted = True
        task.last_modified_by = user_id
        await db.flush()

    @staticmethod
    async def add_task_comment(
        db: AsyncSession, task_id: str, user_id: str, comment_in: TaskCommentCreate
    ) -> dict:
        task = await TaskService.get_task(db, task_id, user_id)
        role = await project_service.check_project_access(db, task.project_id, user_id)
        if role not in ["OWNER", "ADMIN", "MEMBER", "VIEWER"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add comments",
            )

        comment = TaskComment(
            task_id=task_id,
            user_id=user_id,
            content=comment_in.content
        )
        db.add(comment)
        await db.flush()
        await db.refresh(comment)

        # Get username for response
        stmt = select(User.username).where(User.id == user_id)
        res = await db.execute(stmt)
        username = res.scalar()

        return {
            "id": comment.id,
            "task_id": comment.task_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "username": username
        }

    @staticmethod
    async def get_task_comments(
        db: AsyncSession, task_id: str, user_id: str
    ) -> List[dict]:
        task = await TaskService.get_task(db, task_id, user_id)
        
        stmt = (
            select(TaskComment, User.username)
            .outerjoin(User, User.id == TaskComment.user_id)
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at.asc())
        )
        res = await db.execute(stmt)
        rows = res.all()
        
        return [
            {
                "id": c.id,
                "task_id": c.task_id,
                "user_id": c.user_id,
                "content": c.content,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "username": username
            }
            for c, username in rows
        ]


task_service = TaskService()
