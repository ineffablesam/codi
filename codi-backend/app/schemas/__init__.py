"""Pydantic schemas package."""
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserInDB,
    TokenResponse,
    GitHubOAuthCallback,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    ProjectListResponse,
)
from app.schemas.agent import (
    AgentTaskRequest,
    AgentTaskResponse,
    WebSocketMessage,
    AgentStatusMessage,
    FileOperationMessage,
    GitOperationMessage,
    BuildProgressMessage,
    DeploymentCompleteMessage,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "UserInDB",
    "TokenResponse",
    "GitHubOAuthCallback",
    # Project schemas
    "ProjectCreate",
    "ProjectResponse",
    "ProjectUpdate",
    "ProjectListResponse",
    # Agent schemas
    "AgentTaskRequest",
    "AgentTaskResponse",
    "WebSocketMessage",
    "AgentStatusMessage",
    "FileOperationMessage",
    "GitOperationMessage",
    "BuildProgressMessage",
    "DeploymentCompleteMessage",
]
