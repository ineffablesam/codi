"""Implementation plan and task database models."""
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class PlanStatus(str, Enum):
    """Plan status enumeration."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ImplementationPlan(Base):
    """Implementation plan with TODO tracking and user approval workflow."""

    __tablename__ = "implementation_plans"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to project
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Plan metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    walkthrough_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[PlanStatus] = mapped_column(
        SQLEnum(
            "pending_review",
            "approved",
            "rejected",
            "in_progress",
            "completed",
            "failed",
            name="planstatus",
        ),
        default="pending_review",
        nullable=False,
        index=True,
    )

    # Progress tracking
    estimated_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="plans", lazy="selectin")
    tasks: Mapped[List["PlanTask"]] = relationship(
        "PlanTask",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PlanTask.order_index",
    )

    def __repr__(self) -> str:
        """String representation of ImplementationPlan."""
        return f"<ImplementationPlan(id={self.id}, title='{self.title}', status={self.status})>"

    @property
    def progress(self) -> float:
        """Calculate completion progress as a decimal (0.0 to 1.0)."""
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "user_request": self.user_request,
            "status": self.status if isinstance(self.status, str) else self.status.value,
            "estimated_time": self.estimated_time,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "progress": self.progress,
            "file_path": self.file_path,
            "walkthrough_path": self.walkthrough_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": [task.to_dict() for task in self.tasks] if self.tasks else [],
        }


class PlanTask(Base):
    """Individual task within an implementation plan."""

    __tablename__ = "plan_tasks"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to plan
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("implementation_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Task details
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Completion status
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    plan: Mapped["ImplementationPlan"] = relationship(
        "ImplementationPlan", back_populates="tasks", lazy="selectin"
    )

    def __repr__(self) -> str:
        """String representation of PlanTask."""
        status = "✓" if self.completed else "○"
        return f"<PlanTask(id={self.id}, [{status}] {self.description[:30]}...)>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "plan_id": self.plan_id,
            "category": self.category,
            "description": self.description,
            "order_index": self.order_index,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
