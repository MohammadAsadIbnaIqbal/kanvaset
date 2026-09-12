import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Board(Base):
    __tablename__ = "boards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revision = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    workspace = relationship("Workspace", back_populates="boards")
    members = relationship("BoardMember", back_populates="board", cascade="all, delete-orphan")
    objects = relationship("BoardObject", back_populates="board", cascade="all, delete-orphan")
    operations = relationship("BoardOperation", back_populates="board", cascade="all, delete-orphan")


class BoardMember(Base):
    __tablename__ = "board_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    board_id = Column(String(36), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="EDITOR", nullable=False)  # OWNER, EDITOR, VIEWER
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    board = relationship("Board", back_populates="members")
    user = relationship("User", back_populates="board_memberships")

    __table_args__ = (
        UniqueConstraint("board_id", "user_id", name="uq_board_user"),
    )
