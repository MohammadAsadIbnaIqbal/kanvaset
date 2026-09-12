import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class BoardOperation(Base):
    __tablename__ = "board_operations"
    __table_args__ = (
        Index("ix_board_operations_board_revision", "board_id", "revision"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    operation_id = Column(String(64), index=True, nullable=False)
    op_type = Column(String(50), nullable=False)  # e.g., OBJECT_CREATED, OBJECT_MOVED, OBJECT_UPDATED, etc.
    payload = Column(JSON, default=dict, nullable=False)
    revision = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    board = relationship("Board", back_populates="operations")
