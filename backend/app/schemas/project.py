from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectMemberAdd(BaseModel):
    user_email_or_username: str
    role: str = Field(default="MEMBER", pattern="^(OWNER|ADMIN|MEMBER|VIEWER)$")


class ProjectMemberOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    role: str
    username: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    revision: int
    created_at: datetime
    updated_at: datetime
    role: Optional[str] = None
    tasks_count: Optional[int] = 0

    class Config:
        from_attributes = True
