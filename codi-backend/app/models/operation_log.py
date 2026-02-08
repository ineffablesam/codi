"""Operation log database model for audit trail."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project


class OperationType(str, Enum):
    """Types of operations that can be logged."""

    # Agent operations (simplified)
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    TOOL_EXECUTION = "tool_execution"

    # File operations
    FILE_READ = "file_read"
    FILE_CREATED = "file_created"
    FILE_UPDATED = "file_updated"
    FILE_DELETED = "file_deleted"

    # Git operations
    COMMIT_CREATED = "commit_created"

    # Build/Deploy operations
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"

    # Project operations
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"

    # Messages
    USER_MESSAGE = "user_message"
    AGENT_RESPONSE = "agent_response"


class AgentType(str, Enum):
    """Agent types - simplified to single agent."""

    CODI = "codi"  # Main coding agent
    SYSTEM = "system"
    USER = "user"


class OperationLog(Base):
    """Operation log model for tracking agent and system operations."""

    __tablename__ = "operation_logs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Operation metadata
    operation_type: Mapped[OperationType] = mapped_column(
        SQLEnum(
            OperationType,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(
            AgentType,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )

    # Operation details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="completed"
    )  # started, completed, failed

    # Flexible metadata storage
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # File-specific fields
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lines_added: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lines_removed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Git-specific fields
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Duration tracking
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="operation_logs", lazy="selectin")
    project: Mapped["Project"] = relationship(
        "Project", back_populates="operation_logs", lazy="selectin"
    )

    def __repr__(self) -> str:
        """String representation of OperationLog."""
        return (
            f"<OperationLog(id={self.id}, type={self.operation_type.value}, "
            f"agent={self.agent_type.value})>"
        )

    def to_dict(self) -> dict:
        """Convert operation log to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "operation_type": self.operation_type.value,
            "agent_type": self.agent_type.value,
            "message": self.message,
            "status": self.status,
            "details": self.details,
            "file_path": self.file_path,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "commit_sha": self.commit_sha,
            "branch_name": self.branch_name,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_websocket_message(self) -> dict:
        """Convert to WebSocket message format for frontend."""
        base_message = {
            "timestamp": self.created_at.isoformat() if self.created_at else None,
            "agent": self.agent_type.value,
            "message": self.message,
            "status": self.status,
        }

        operation_value = self.operation_type.value

        if operation_value in ["file_created", "file_updated", "file_deleted"]:
            base_message["type"] = "file_operation"
            base_message["operation"] = operation_value.replace("file_", "")
            base_message["file_path"] = self.file_path
            if self.lines_added is not None or self.lines_removed is not None:
                base_message["stats"] = f"+{self.lines_added or 0}/-{self.lines_removed or 0}"

        elif operation_value == "commit_created":
            base_message["type"] = "git_operation"
            base_message["operation"] = operation_value
            base_message["branch_name"] = self.branch_name
            base_message["commit_sha"] = self.commit_sha

        elif operation_value == "tool_execution":
            base_message["type"] = "tool_execution"
            base_message["tool"] = self.details.get("tool") if self.details else None

        elif operation_value == "deployment_completed":
            base_message["type"] = "deployment_complete"
            base_message["deployment_url"] = self.details.get("deployment_url") if self.details else None

        elif self.status == "failed" or operation_value.endswith("_failed"):
            base_message["type"] = "agent_error"
            base_message["error"] = self.error_message

        else:
            base_message["type"] = "agent_status"
            base_message["details"] = self.details

        return base_message
