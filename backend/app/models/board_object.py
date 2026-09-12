import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class BoardObject(Base):
    __tablename__ = "board_objects"

    # ID can be a UUID or stable client string ID
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # rectangle, circle, sticky_note, text, connector, etc.
    
    # Coordinate and dimension space
    x = Column(Float, default=0.0, nullable=False)
    y = Column(Float, default=0.0, nullable=False)
    width = Column(Float, default=100.0, nullable=False)
    height = Column(Float, default=100.0, nullable=False)
    rotation = Column(Float, default=0.0, nullable=False)
    z_index = Column(Integer, default=0, nullable=False)

    # Style and content
    color = Column(String(50), default="#ffffff", nullable=True)
    fill = Column(String(50), default="#ffffff", nullable=True)
    stroke = Column(String(50), default="#000000", nullable=True)
    stroke_width = Column(Float, default=1.5, nullable=False)
    text = Column(Text, default="", nullable=True)
    
    # Flexible JSON properties (e.g. fontSize, fontFamily, connectorStartId, connectorEndId, etc.)
    properties = Column(JSON, default=dict, nullable=False)

    # Optimistic concurrency and soft delete
    version = Column(Integer, default=1, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_modified_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    board = relationship("Board", back_populates="objects")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "board_id": self.board_id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "z_index": self.z_index,
            "color": self.color,
            "fill": self.fill,
            "stroke": self.stroke,
            "stroke_width": self.stroke_width,
            "text": self.text or "",
            "properties": self.properties or {},
            "version": self.version,
            "is_deleted": self.is_deleted,
            "created_by": self.created_by,
            "last_modified_by": self.last_modified_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
