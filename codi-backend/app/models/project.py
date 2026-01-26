"""Project database model."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.operation_log import OperationLog
    from app.models.backend_connection import ProjectBackendConfig
    from app.models.container import Container
    from app.models.deployment import Deployment
    from app.models.plan import ImplementationPlan


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

    # Local Git repository (Codi-managed)
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # /var/codi/repos/user_id/project_slug
    git_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # Current HEAD commit
    git_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")  # Current branch

    # Project settings
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    framework_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dart_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Multi-platform configuration
    platform_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="mobile", index=True
    )  # mobile, web
    framework: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, default="flutter", index=True
    )  # flutter, react, nextjs, react_native
    backend_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # supabase, firebase, serverpod
    backend_config: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Encrypted JSON with API keys and configuration
    deployment_platform: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # github_pages, vercel, netlify

    # Project status
    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum("active", "building", "deploying", "archived", "error", name="projectstatus"),
        default="active",
        nullable=False,
        index=True,
    )

    # Initial project setup stage (for multi-chat blocking)
    # pending -> deploying_starter -> building_idea -> deploying_final -> completed
    setup_stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="completed"
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
    backend_configs: Mapped[List["ProjectBackendConfig"]] = relationship(
        "ProjectBackendConfig",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    containers: Mapped[List["Container"]] = relationship(
        "Container",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    deployments: Mapped[List["Deployment"]] = relationship(
        "Deployment",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    plans: Mapped[List["ImplementationPlan"]] = relationship(
        "ImplementationPlan",
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
            # Local Git repository
            "local_path": self.local_path,
            "git_commit_sha": self.git_commit_sha,
            "git_branch": self.git_branch,
            "is_private": self.is_private,
            # Multi-platform configuration
            "platform_type": self.platform_type,
            "framework": self.framework,
            "backend_type": self.backend_type,
            "deployment_platform": self.deployment_platform,
            # Note: backend_config is encrypted and not exposed directly
            "deployment_url": self.deployment_url,
            "deployment_provider": self.deployment_provider,
            "last_deployment_at": (
                self.last_deployment_at.isoformat() if self.last_deployment_at else None
            ),
            "last_build_status": self.last_build_status,
            "last_build_at": self.last_build_at.isoformat() if self.last_build_at else None,
            "status": self.status if isinstance(self.status, str) else self.status.value,
            "setup_stage": self.setup_stage,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

