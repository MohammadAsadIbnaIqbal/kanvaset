from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None


class BoardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None


class BoardMemberAdd(BaseModel):
    user_email_or_username: str
    role: str = Field(default="EDITOR", pattern="^(OWNER|EDITOR|VIEWER)$")


class BoardMemberUpdate(BaseModel):
    role: str = Field(..., pattern="^(OWNER|EDITOR|VIEWER)$")


class BoardMemberOut(BaseModel):
    id: str
    board_id: str
    user_id: str
    role: str  # OWNER, EDITOR, VIEWER
    username: str
    email: str
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BoardOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: Optional[str] = None
    revision: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    role: Optional[str] = "EDITOR"
    objects_count: Optional[int] = 0
    workspace_name: Optional[str] = None
    owner_username: Optional[str] = None

    class Config:
        from_attributes = True
