"""Project-related Pydantic schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.project import ProjectStatus


class ProjectBase(BaseModel):
    """Base project schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    is_private: bool = False


class ProjectUpdate(BaseModel):
    """Schema for updating project information."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    """Schema for project API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: Optional[str] = None
    github_repo_name: Optional[str] = None
    github_repo_url: Optional[str] = None
    github_repo_full_name: Optional[str] = None
    github_clone_url: Optional[str] = None
    github_default_branch: Optional[str] = None
    github_current_branch: Optional[str] = None
    is_private: bool = False
    framework_version: Optional[str] = None
    dart_version: Optional[str] = None
    deployment_url: Optional[str] = None
    deployment_provider: Optional[str] = None
    last_deployment_at: Optional[datetime] = None
    last_build_status: Optional[str] = None
    last_build_at: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Schema for paginated project list response."""

    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ProjectWithOwner(ProjectResponse):
    """Schema for project with owner information."""

    owner_username: str
    owner_avatar_url: Optional[str] = None


class GitHubRepoInfo(BaseModel):
    """Schema for GitHub repository information."""

    name: str
    full_name: str
    html_url: str
    clone_url: str
    default_branch: str
    private: bool


class DeploymentInfo(BaseModel):
    """Schema for deployment information."""

    url: str
    provider: str  # 'github_pages' or 'vercel'
    status: str  # 'pending', 'deployed', 'failed'
    deployed_at: Optional[datetime] = None
    build_time_seconds: Optional[int] = None
    size_bytes: Optional[int] = None


class BuildInfo(BaseModel):
    """Schema for build information."""

    status: str  # 'pending', 'running', 'success', 'failed'
    workflow_name: str
    workflow_url: Optional[str] = None
    commit_sha: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Optional[float] = None  # 0.0 to 1.0
