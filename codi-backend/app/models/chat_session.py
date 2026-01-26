"""Chat session and message models for multi-chat support."""
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ChatSession(Base):
    """Chat session model for multi-chat support.
    
    Each project can have multiple chat sessions, allowing users to organize
    conversations by topic or task.
    """

    __tablename__ = "chat_sessions"

    # Primary key - UUID for better distribution
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign keys
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Session metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Mem0 integration - unique identifier for this session in Mem0
    mem0_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Soft delete and archival
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Additional metadata (JSON)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessage.created_at",
    )
    memories: Mapped[List["AgentMemory"]] = relationship(
        "AgentMemory",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title='{self.title}', project_id={self.project_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "title": self.title,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "meta_data": self.meta_data or {},
        }


class ChatMessage(Base):
    """Individual message within a chat session.
    
    Stores both user and assistant messages with optional tool call data.
    """

    __tablename__ = "chat_messages"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign key to session
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'user', 'assistant', 'system'
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Tool calls for assistant messages (stores tool name, args, results)
    tool_calls: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Additional metadata
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Relationship
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages", lazy="selectin"
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(id={self.id}, role='{self.role}', content='{preview}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "meta_data": self.meta_data or {},
        }


class AgentMemory(Base):
    """Memory records synced with Mem0.ai.
    
    Tracks memories created during agent interactions for persistence
    and retrieval across sessions.
    """

    __tablename__ = "agent_memories"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # Foreign keys (optional session - memories can be project-wide)
    session_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Memory type classification
    memory_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'task', 'decision', 'learning', 'project_context', 'deployment'

    # Memory content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Mem0 reference ID for sync
    mem0_memory_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Additional metadata
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Relationships
    session: Mapped[Optional["ChatSession"]] = relationship(
        "ChatSession", back_populates="memories", lazy="selectin"
    )
    project: Mapped["Project"] = relationship("Project", lazy="selectin")

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<AgentMemory(id={self.id}, type='{self.memory_type}', content='{preview}')>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "project_id": self.project_id,
            "memory_type": self.memory_type,
            "content": self.content,
            "mem0_memory_id": self.mem0_memory_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "meta_data": self.meta_data or {},
        }
