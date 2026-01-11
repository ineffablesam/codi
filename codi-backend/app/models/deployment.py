"""Deployment database model for tracking project deployments."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.container import Container


class DeploymentStatus(str, Enum):
    """Deployment lifecycle status."""
    PENDING = "pending"          # Waiting to start
    BUILDING = "building"        # Image being built
    DEPLOYING = "deploying"      # Container being created/started
    ACTIVE = "active"            # Deployment live and serving traffic
    INACTIVE = "inactive"        # Deployment stopped but container exists
    FAILED = "failed"            # Deployment failed
    DESTROYED = "destroyed"      # Deployment and container removed


class Deployment(Base):
    """Deployment model for project subdomain routing."""
    
    __tablename__ = "deployments"
    
    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    
    # Relationships
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    container_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("containers.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Subdomain configuration
    subdomain: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Status
    status: Mapped[DeploymentStatus] = mapped_column(
        SQLEnum(DeploymentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DeploymentStatus.PENDING,
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Framework info
    framework: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    
    # Git reference
    git_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    git_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    
    # Flags
    is_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_production: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="deployments")
    container: Mapped[Optional["Container"]] = relationship("Container", back_populates="deployment")
    
    def __repr__(self) -> str:
        return f"<Deployment {self.subdomain} ({self.status.value})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "container_id": self.container_id,
            "subdomain": self.subdomain,
            "url": self.url,
            "status": self.status.value,
            "status_message": self.status_message,
            "framework": self.framework,
            "git_commit_sha": self.git_commit_sha,
            "git_branch": self.git_branch,
            "is_preview": self.is_preview,
            "is_production": self.is_production,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
        }
