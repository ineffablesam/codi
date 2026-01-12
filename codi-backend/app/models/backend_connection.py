"""Backend connection model for OAuth-linked services."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.services.domain.encryption import encryption_service


class BackendConnection(Base):
    """Stores user's OAuth connections to backend providers (Supabase, Firebase)."""

    __tablename__ = "backend_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'supabase', 'firebase'
    
    # Encrypted OAuth tokens
    access_token = Column(LargeBinary, nullable=True)
    refresh_token = Column(LargeBinary, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Provider-specific identifiers
    provider_user_id = Column(String(255), nullable=True)
    organization_id = Column(String(255), nullable=True)  # Supabase org / Firebase project parent
    
    # Connection status
    is_connected = Column(String(20), default="pending")  # pending, connected, expired, error
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="backend_connections")

    def set_access_token(self, token: str) -> None:
        """Encrypt and store access token."""
        self.access_token = encryption_service.encrypt(token).encode("utf-8")

    def get_access_token(self) -> Optional[str]:
        """Decrypt and return access token."""
        if self.access_token:
            return encryption_service.decrypt(self.access_token.decode("utf-8"))
        return None

    def set_refresh_token(self, token: str) -> None:
        """Encrypt and store refresh token."""
        self.refresh_token = encryption_service.encrypt(token).encode("utf-8")

    def get_refresh_token(self) -> Optional[str]:
        """Decrypt and return refresh token."""
        if self.refresh_token:
            return encryption_service.decrypt(self.refresh_token.decode("utf-8"))
        return None

    @property
    def is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self.token_expires_at:
            return True
        return datetime.now(timezone.utc) >= self.token_expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary (without sensitive data)."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "is_connected": self.is_connected,
            "organization_id": self.organization_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectBackendConfig(Base):
    """Stores backend configuration for a specific project."""

    __tablename__ = "project_backend_configs"
    __table_args__ = (
        UniqueConstraint("project_id", "provider", name="uq_project_provider"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'supabase', 'firebase', 'serverpod'
    
    # Provider project identifiers
    provider_project_id = Column(String(255), nullable=True)  # e.g., Supabase project ref
    provider_project_url = Column(Text, nullable=True)  # e.g., https://xxx.supabase.co
    
    # Encrypted API keys (for runtime use by agents)
    api_key_anon = Column(LargeBinary, nullable=True)  # Public/anon key
    api_key_service = Column(LargeBinary, nullable=True)  # Service role key
    
    # Configuration JSON (encrypted) - stores full config
    config_data = Column(LargeBinary, nullable=True)
    
    # Status
    status = Column(String(20), default="pending")  # pending, provisioning, active, error
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    project = relationship("Project", back_populates="backend_configs")

    def set_api_key_anon(self, key: str) -> None:
        """Encrypt and store anon key."""
        self.api_key_anon = encryption_service.encrypt(key).encode("utf-8")

    def get_api_key_anon(self) -> Optional[str]:
        """Decrypt and return anon key."""
        if self.api_key_anon:
            return encryption_service.decrypt(self.api_key_anon.decode("utf-8"))
        return None

    def set_api_key_service(self, key: str) -> None:
        """Encrypt and store service key."""
        self.api_key_service = encryption_service.encrypt(key).encode("utf-8")

    def get_api_key_service(self) -> Optional[str]:
        """Decrypt and return service key."""
        if self.api_key_service:
            return encryption_service.decrypt(self.api_key_service.decode("utf-8"))
        return None

    def set_config_data(self, data: dict) -> None:
        """Encrypt and store config JSON."""
        import json
        self.config_data = encryption_service.encrypt(json.dumps(data)).encode("utf-8")

    def get_config_data(self) -> Optional[dict]:
        """Decrypt and return config JSON."""
        if self.config_data:
            import json
            return json.loads(encryption_service.decrypt(self.config_data.decode("utf-8")))
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary (without sensitive data)."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "provider": self.provider,
            "provider_project_id": self.provider_project_id,
            "provider_project_url": self.provider_project_url,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
