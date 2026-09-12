from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BoardObjectCreate(BaseModel):
    id: str
    type: str
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0
    z_index: int = 0
    color: Optional[str] = "#ffffff"
    fill: Optional[str] = "#ffffff"
    stroke: Optional[str] = "#000000"
    stroke_width: float = 1.5
    text: Optional[str] = ""
    properties: Dict[str, Any] = Field(default_factory=dict)


class BoardObjectUpdate(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None
    z_index: Optional[int] = None
    color: Optional[str] = None
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: Optional[float] = None
    text: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    version: Optional[int] = None


class BoardObjectOut(BaseModel):
    id: str
    board_id: str
    type: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    z_index: int
    color: Optional[str] = None
    fill: Optional[str] = None
    stroke: Optional[str] = None
    stroke_width: float
    text: str
    properties: Dict[str, Any]
    version: int
    is_deleted: bool
    created_by: Optional[str] = None
    last_modified_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
