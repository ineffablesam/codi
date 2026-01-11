"""Container database model for tracking Docker containers."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class ContainerStatus(str, Enum):
    """Container lifecycle status."""
    PENDING = "pending"      # Waiting to be created
    BUILDING = "building"    # Image being built
    CREATED = "created"      # Container created but not started
    RUNNING = "running"      # Container running
    STOPPED = "stopped"      # Container stopped
    ERROR = "error"          # Container in error state
    DESTROYED = "destroyed"  # Container removed


class Container(Base):
    """Docker container model for project deployments."""
    
    __tablename__ = "containers"
    
    # Primary key - Docker container ID
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # Relationships
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Container metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    image: Mapped[str] = mapped_column(String(500), nullable=False)
    image_tag: Mapped[str] = mapped_column(String(255), nullable=False, default="latest")
    
    # Status
    status: Mapped[ContainerStatus] = mapped_column(
        SQLEnum(ContainerStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ContainerStatus.PENDING,
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Git reference
    git_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    git_branch: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    
    # Network configuration
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    host_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Resource limits
    cpu_limit: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=512)
    
    # Flags
    is_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_restart: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Build info
    build_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    build_logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="containers")
    deployment: Mapped[Optional["Deployment"]] = relationship("Deployment", back_populates="container", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Container {self.name} ({self.status.value})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "image": self.image,
            "image_tag": self.image_tag,
            "status": self.status.value,
            "status_message": self.status_message,
            "git_commit_sha": self.git_commit_sha,
            "git_branch": self.git_branch,
            "port": self.port,
            "host_port": self.host_port,
            "cpu_limit": self.cpu_limit,
            "memory_limit_mb": self.memory_limit_mb,
            "is_preview": self.is_preview,
            "auto_restart": self.auto_restart,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "build_duration_seconds": self.build_duration_seconds,
        }


# Import for type hints
from app.models.deployment import Deployment
