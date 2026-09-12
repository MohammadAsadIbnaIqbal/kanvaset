from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class WorkspaceMemberAdd(BaseModel):
    user_email_or_username: str
    role: str = Field(default="MEMBER", pattern="^(OWNER|ADMIN|MEMBER)$")


class WorkspaceMemberOut(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    username: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkspaceOut(BaseModel):
    id: str
    name: str
    owner_id: str
    created_at: datetime
    role: Optional[str] = "OWNER"
    members_count: Optional[int] = 1
    boards_count: Optional[int] = 0

    class Config:
        from_attributes = True
