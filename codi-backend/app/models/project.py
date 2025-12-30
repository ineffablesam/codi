"""Project database model."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.operation_log import OperationLog


class ProjectStatus(str, Enum):
    """Project status enum matching database."""

    ACTIVE = "active"
    BUILDING = "building"
    DEPLOYING = "deploying"
    ARCHIVED = "archived"
    ERROR = "error"


class Project(Base):
    """Project model representing a user's coding project."""

    __tablename__ = "projects"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Project metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign key to user
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # GitHub integration
    github_repo_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_repo_full_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    github_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_clone_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_default_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="main")
    github_current_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="main")

    # Project settings
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    framework_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dart_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Project status
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum("active", "building", "deploying", "archived", "error", name="projectstatus"),
        default="active",
        nullable=False,
        index=True,
    )

    # Deployment info
    deployment_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    deployment_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_deployment_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Build info
    last_build_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_build_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects", lazy="selectin")
    operation_logs: Mapped[List["OperationLog"]] = relationship(
        "OperationLog",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of Project."""
        return f"<Project(id={self.id}, name='{self.name}', status={self.status})>"

    def to_dict(self) -> dict:
        """Convert project to dictionary."""
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "description": self.description,
            "github_repo_name": self.github_repo_name,
            "github_repo_url": self.github_repo_url,
            "github_repo_full_name": self.github_repo_full_name,
            "github_clone_url": self.github_clone_url,
            "github_default_branch": self.github_default_branch,
            "github_current_branch": self.github_current_branch,
            "is_private": self.is_private,
            "deployment_url": self.deployment_url,
            "deployment_provider": self.deployment_provider,
            "last_deployment_at": (
                self.last_deployment_at.isoformat() if self.last_deployment_at else None
            ),
            "last_build_status": self.last_build_status,
            "last_build_at": self.last_build_at.isoformat() if self.last_build_at else None,
            "status": self.status if isinstance(self.status, str) else self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
