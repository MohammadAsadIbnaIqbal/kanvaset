from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = Field("TODO")
    priority: Optional[str] = Field("MEDIUM")
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskOut(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    tags: List[str]
    version: int
    is_deleted: bool
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskCommentCreate(BaseModel):
    content: str = Field(..., min_length=1)


class TaskCommentOut(BaseModel):
    id: str
    task_id: str
    user_id: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime
    username: Optional[str] = None

    class Config:
        from_attributes = True
