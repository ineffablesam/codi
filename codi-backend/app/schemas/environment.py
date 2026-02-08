"""Pydantic schemas for environment variable management."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EnvironmentVariableBase(BaseModel):
    """Base schema for environment variables."""
    
    key: str = Field(..., min_length=1, max_length=255, description="Environment variable key")
    value: str = Field(..., description="Environment variable value")
    context: str = Field(
        default="general",
        description="Context where this variable is used (docker-compose, server-config, flutter-build, general)"
    )
    is_secret: bool = Field(default=False, description="Whether this value should be encrypted")
    description: Optional[str] = Field(None, description="Optional description of the variable")

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """Validate environment variable key format."""
        # Must be uppercase letters, numbers, and underscores only
        if not all(c.isupper() or c.isdigit() or c == "_" for c in v):
            raise ValueError(
                "Environment variable key must contain only uppercase letters, numbers, and underscores"
            )
        if v[0].isdigit():
            raise ValueError("Environment variable key cannot start with a number")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: str) -> str:
        """Validate context is one of the allowed values."""
        allowed = {"docker-compose", "server-config", "flutter-build", "general"}
        if v not in allowed:
            raise ValueError(f"Context must be one of: {', '.join(allowed)}")
        return v


class EnvironmentVariableCreate(EnvironmentVariableBase):
    """Schema for creating a new environment variable."""
    pass


class EnvironmentVariableUpdate(BaseModel):
    """Schema for updating an environment variable."""
    
    value: Optional[str] = Field(None, description="New value for the variable")
    context: Optional[str] = Field(None, description="New context for the variable")
    is_secret: Optional[bool] = Field(None, description="Update secret flag")
    description: Optional[str] = Field(None, description="Update description")

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: Optional[str]) -> Optional[str]:
        """Validate context if provided."""
        if v is not None:
            allowed = {"docker-compose", "server-config", "flutter-build", "general"}
            if v not in allowed:
                raise ValueError(f"Context must be one of: {', '.join(allowed)}")
        return v


class EnvironmentVariableResponse(EnvironmentVariableBase):
    """Schema for environment variable responses."""
    
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnvironmentVariableListResponse(BaseModel):
    """Schema for list of environment variables."""
    
    variables: list[EnvironmentVariableResponse]
    total: int


class EnvironmentSyncRequest(BaseModel):
    """Schema for syncing environment variables to .env file."""
    
    context: Optional[str] = Field(
        None,
        description="Only sync variables with this context. If None, sync all contexts."
    )
    include_secrets: bool = Field(
        default=True,
        description="Whether to include secret values in the sync"
    )


class EnvironmentSyncResponse(BaseModel):
    """Schema for environment sync response."""
    
    success: bool
    message: str
    synced_count: int
    file_path: str
