"""User-related Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    github_username: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=255)
    github_avatar_url: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user from GitHub OAuth."""

    github_id: int
    github_access_token_encrypted: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, max_length=255)
    github_avatar_url: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    github_id: int
    github_username: str
    email: Optional[str] = None
    name: Optional[str] = None
    github_avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserInDB(UserResponse):
    """Schema for user with database fields (internal use)."""

    github_access_token_encrypted: Optional[str] = None


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class GitHubOAuthCallback(BaseModel):
    """Schema for GitHub OAuth callback."""

    code: str
    state: Optional[str] = None


class GitHubUserInfo(BaseModel):
    """Schema for GitHub user information from API."""

    id: int
    login: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    html_url: Optional[str] = None


class GitHubTokenResponse(BaseModel):
    """Schema for GitHub OAuth token response."""

    access_token: str
    token_type: str
    scope: str
