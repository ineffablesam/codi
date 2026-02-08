"""Environment variable database model for project-specific configuration."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from cryptography.fernet import Fernet
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


class EnvironmentVariable(Base):
    """Environment variable model for storing project-specific configuration.
    
    Supports multiple contexts (docker-compose, server-config, flutter-build) and
    automatic encryption for sensitive values.
    """

    __tablename__ = "environment_variables"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to project
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Environment variable data
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted if is_secret=True
    
    # Context indicates where this variable is used
    # - "docker-compose": For docker-compose.yml environment substitution
    # - "server-config": For Serverpod server config files (development.yaml, production.yaml)
    # - "flutter-build": For Flutter build-time --dart-define variables
    # - "general": For general use across all contexts
    context: Mapped[str] = mapped_column(
        String(50), nullable=False, default="general", index=True
    )
    
    # Security flag
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Description/documentation for this variable
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    project: Mapped["Project"] = relationship(
        "Project", back_populates="environment_variables"
    )

    def __repr__(self) -> str:
        """String representation of EnvironmentVariable."""
        value_display = "***" if self.is_secret else self.value[:20]
        return f"<EnvironmentVariable(id={self.id}, key='{self.key}', context='{self.context}', value='{value_display}')>"

    @staticmethod
    def _get_cipher() -> Fernet:
        """Get Fernet cipher for encryption/decryption.
        
        Returns:
            Fernet cipher instance
        """
        # Use the encryption key from settings
        encryption_key = getattr(settings, 'encryption_key', None)
        if not encryption_key:
            # Generate a key if not configured (for development only)
            encryption_key = Fernet.generate_key()
        
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        return Fernet(encryption_key)

    def set_value(self, value: str, is_secret: bool = False) -> None:
        """Set the value, encrypting if it's a secret.
        
        Args:
            value: Value to store
            is_secret: Whether to encrypt the value
        """
        self.is_secret = is_secret
        if is_secret:
            cipher = self._get_cipher()
            encrypted = cipher.encrypt(value.encode())
            self.value = encrypted.decode()
        else:
            self.value = value

    def get_value(self) -> str:
        """Get the decrypted value.
        
        Returns:
            Decrypted value
        """
        if self.is_secret:
            cipher = self._get_cipher()
            try:
                decrypted = cipher.decrypt(self.value.encode())
                return decrypted.decode()
            except Exception:
                # If decryption fails, return the raw value (might be unencrypted legacy data)
                return self.value
        return self.value

    def to_dict(self, include_value: bool = True, decrypt: bool = True) -> dict:
        """Convert environment variable to dictionary.
        
        Args:
            include_value: Whether to include the value in the output
            decrypt: Whether to decrypt secret values (only if include_value=True)
        
        Returns:
            Dictionary representation
        """
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "key": self.key,
            "context": self.context,
            "is_secret": self.is_secret,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_value:
            if decrypt:
                result["value"] = self.get_value()
            else:
                # Return masked value for secrets in non-decrypted mode
                result["value"] = "***" if self.is_secret else self.value
        
        return result
