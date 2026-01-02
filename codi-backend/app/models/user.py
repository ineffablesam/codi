"""User database model."""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.operation_log import OperationLog
    from app.models.backend_connection import BackendConnection


class User(Base):
    """User model representing a Codi platform user."""

    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # GitHub OAuth fields
    github_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    github_username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Encrypted GitHub access token (encrypted using Fernet)
    github_access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # User metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    operation_logs: Mapped[List["OperationLog"]] = relationship(
        "OperationLog",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    backend_connections: Mapped[List["BackendConnection"]] = relationship(
        "BackendConnection",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, github_username='{self.github_username}')>"

    def to_dict(self) -> dict:
        """Convert user to dictionary (excluding sensitive fields)."""
        return {
            "id": self.id,
            "github_id": self.github_id,
            "github_username": self.github_username,
            "email": self.email,
            "name": self.name,
            "github_avatar_url": self.github_avatar_url,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
