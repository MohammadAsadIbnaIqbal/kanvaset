from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.schemas.task import (
    TaskCreate,
    TaskOut,
    TaskUpdate,
    TaskCommentCreate,
    TaskCommentOut,
)
from backend.app.services.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/project/{project_id}", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: str,
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await task_service.create_task(
        db, project_id=project_id, user_id=current_user.id, task_in=task_in
    )
    return TaskOut.model_validate(task)

@router.get("/project/{project_id}", response_model=List[TaskOut])
async def list_project_tasks(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = await task_service.get_project_tasks(db, project_id=project_id, user_id=current_user.id)
    return [TaskOut.model_validate(t) for t in tasks]

@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await task_service.get_task(db, task_id=task_id, user_id=current_user.id)
    return TaskOut.model_validate(task)

@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    task_in: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await task_service.update_task(
        db, task_id=task_id, user_id=current_user.id, task_in=task_in
    )
    return TaskOut.model_validate(task)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await task_service.delete_task(db, task_id=task_id, user_id=current_user.id)

@router.post("/{task_id}/comments", response_model=TaskCommentOut, status_code=status.HTTP_201_CREATED)
async def add_task_comment(
    task_id: str,
    comment_in: TaskCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = await task_service.add_task_comment(
        db, task_id=task_id, user_id=current_user.id, comment_in=comment_in
    )
    return TaskCommentOut(**comment)

@router.get("/{task_id}/comments", response_model=List[TaskCommentOut])
async def list_task_comments(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comments = await task_service.get_task_comments(db, task_id=task_id, user_id=current_user.id)
    return [TaskCommentOut(**c) for c in comments]

@router.get("/{task_id}/history")
async def get_task_history(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from backend.app.models.history import TaskVersion
    from sqlalchemy import select
    stmt = select(TaskVersion).where(TaskVersion.task_id == task_id).order_by(TaskVersion.revision.desc())
    res = await db.execute(stmt)
    return [{"id": r.id, "revision": r.revision, "snapshot": r.snapshot, "created_at": r.created_at} for r in res.scalars().all()]
