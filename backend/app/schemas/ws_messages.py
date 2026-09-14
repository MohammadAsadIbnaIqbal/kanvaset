from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WSMessageType(str, Enum):
    # State mutation operations
    OBJECT_CREATED = "OBJECT_CREATED"
    OBJECT_MOVED = "OBJECT_MOVED"
    OBJECT_RESIZED = "OBJECT_RESIZED"
    OBJECT_UPDATED = "OBJECT_UPDATED"
    OBJECT_DELETED = "OBJECT_DELETED"

    # Task & Project Operations
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"
    TASK_COMMENT_ADDED = "TASK_COMMENT_ADDED"
    ACTIVITY_LOGGED = "ACTIVITY_LOGGED"

    # Ephemeral & Presence
    CURSOR_MOVED = "CURSOR_MOVED"
    USER_JOINED = "USER_JOINED"
    USER_LEFT = "USER_LEFT"
    PRESENCE_STATE = "PRESENCE_STATE"

    # Synchronization & State Recovery
    SYNC_REQUEST = "SYNC_REQUEST"
    SYNC_SNAPSHOT = "SYNC_SNAPSHOT"

    # Acknowledgement & Error
    ACK = "ACK"
    ERROR = "ERROR"


class WSMessage(BaseModel):
    type: WSMessageType
    board_id: Optional[str] = None
    project_id: Optional[str] = None
    operation_id: Optional[str] = None
    object_id: Optional[str] = None
    task_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    client_revision: Optional[int] = None
    server_revision: Optional[int] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_color: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class BoardSnapshotPayload(BaseModel):
    board: Dict[str, Any]
    objects: List[Dict[str, Any]]
    presence: List[Dict[str, Any]]
    role: str  # OWNER, EDITOR, VIEWER
    server_revision: int


class CursorPayload(BaseModel):
    x: float
    y: float
    user_id: str
    user_name: str
    user_color: str


class PresenceUser(BaseModel):
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    color: str
    role: str
    joined_at: float

class ProjectSnapshotPayload(BaseModel):
    project: Dict[str, Any]
    tasks: List[Dict[str, Any]]
    presence: List[Dict[str, Any]]
    activities: List[Dict[str, Any]]
    role: str
    server_revision: int
