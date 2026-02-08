"""Opik tracing models for AI operation tracking."""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project


class Trace(Base):
    """AI operation trace for tracking LLM calls and agent actions."""

    __tablename__ = "traces"

    # Primary key
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    parent_trace_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("traces.id", ondelete="CASCADE"), nullable=True)

    # Trace metadata
    trace_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'code_generation', 'summarization', 'debugging', etc.
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timing
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Data
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)  # model, tokens, cost, etc.
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    project: Mapped[Optional["Project"]] = relationship("Project", foreign_keys=[project_id], lazy="selectin")
    evaluations: Mapped[List["Evaluation"]] = relationship("Evaluation", back_populates="trace", cascade="all, delete-orphan", lazy="selectin")
    
    # Self-referential for nested traces
    parent_trace: Mapped[Optional["Trace"]] = relationship("Trace", remote_side=[id], foreign_keys=[parent_trace_id], lazy="selectin")
    child_traces: Mapped[List["Trace"]] = relationship("Trace", back_populates="parent_trace", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Trace(id={self.id}, type={self.trace_type}, name='{self.name}')>"

    def to_dict(self, include_evaluations: bool = True) -> dict:
        """Convert trace to dictionary."""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "parent_trace_id": self.parent_trace_id,
            "trace_type": self.trace_type,
            "name": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "meta_data": self.meta_data,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_evaluations and self.evaluations:
            result["evaluations"] = [e.to_dict() for e in self.evaluations]
        
        return result


class Evaluation(Base):
    """Quality evaluation for a trace."""

    __tablename__ = "evaluations"

    # Primary key
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    trace_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True)

    # Evaluation data
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    trace: Mapped["Trace"] = relationship("Trace", back_populates="evaluations", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Evaluation(id={self.id}, metric={self.metric_name}, score={self.score})>"

    def to_dict(self) -> dict:
        """Convert evaluation to dictionary."""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "metric_name": self.metric_name,
            "score": self.score,
            "reason": self.reason,
            "meta_data": self.meta_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Experiment(Base):
    """Experiment for A/B testing prompts and configurations."""

    __tablename__ = "experiments"

    # Primary key
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Experiment data
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prompt_versions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Experiment(id={self.id}, name='{self.name}')>"


class Prompt(Base):
    """Versioned prompt template."""

    __tablename__ = "prompts"

    # Primary key
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))

    # Prompt identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Prompt content
    template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Prompt(name='{self.name}', version={self.version})>"

    def format(self, **kwargs) -> str:
        """Format the prompt template with provided variables."""
        # Simple variable replacement using {{variable}} syntax
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
