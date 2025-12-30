"""Agent and WebSocket message Pydantic schemas."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    """Agent type enumeration."""

    PLANNER = "planner"
    FLUTTER_ENGINEER = "flutter_engineer"
    CODE_REVIEWER = "code_reviewer"
    GIT_OPERATOR = "git_operator"
    BUILD_DEPLOY = "build_deploy"
    MEMORY = "memory"
    BACKEND_ENGINEER = "backend_engineer"


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    PLANNING = "planning"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageType(str, Enum):
    """WebSocket message type enumeration."""

    AGENT_STATUS = "agent_status"
    TOOL_EXECUTION = "tool_execution"
    FILE_OPERATION = "file_operation"
    GIT_OPERATION = "git_operation"
    BUILD_STATUS = "build_status"
    BUILD_PROGRESS = "build_progress"
    DEPLOYMENT_COMPLETE = "deployment_complete"
    REVIEW_PROGRESS = "review_progress"
    REVIEW_ISSUE = "review_issue"
    AGENT_ERROR = "agent_error"
    USER_INPUT_REQUIRED = "user_input_required"
    USER_MESSAGE = "user_message"
    PING = "ping"
    PONG = "pong"


class AgentTaskRequest(BaseModel):
    """Schema for submitting a task to the agent system."""

    message: str = Field(..., min_length=1, max_length=10000)
    project_id: int


class AgentTaskResponse(BaseModel):
    """Schema for agent task submission response."""

    task_id: str
    status: str = "queued"
    message: str = "Task submitted successfully"


class AgentTaskStatus(BaseModel):
    """Schema for agent task status."""

    task_id: str
    status: str  # 'queued', 'running', 'completed', 'failed'
    progress: Optional[float] = None
    current_agent: Optional[str] = None
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# WebSocket Message Schemas

class WebSocketMessageBase(BaseModel):
    """Base schema for all WebSocket messages."""

    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentStatusMessage(WebSocketMessageBase):
    """Schema for agent status WebSocket messages."""

    type: MessageType = MessageType.AGENT_STATUS
    agent: AgentType
    status: AgentStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class ToolExecutionMessage(WebSocketMessageBase):
    """Schema for tool execution WebSocket messages."""

    type: MessageType = MessageType.TOOL_EXECUTION
    agent: AgentType
    tool: str
    file_path: Optional[str] = None
    message: str


class FileOperationMessage(WebSocketMessageBase):
    """Schema for file operation WebSocket messages."""

    type: MessageType = MessageType.FILE_OPERATION
    agent: AgentType
    operation: str  # 'create', 'update', 'delete'
    file_path: str
    message: str
    details: Optional[Dict[str, Any]] = None  # lines_of_code, widgets, dependencies


class GitOperationMessage(WebSocketMessageBase):
    """Schema for git operation WebSocket messages."""

    type: MessageType = MessageType.GIT_OPERATION
    agent: AgentType = AgentType.GIT_OPERATOR
    operation: str  # 'create_branch', 'commit', 'push', 'merge'
    branch_name: Optional[str] = None
    commit_sha: Optional[str] = None
    message: str
    files_changed: Optional[int] = None
    insertions: Optional[int] = None
    deletions: Optional[int] = None


class BuildStatusMessage(WebSocketMessageBase):
    """Schema for build status WebSocket messages."""

    type: MessageType = MessageType.BUILD_STATUS
    agent: AgentType = AgentType.BUILD_DEPLOY
    status: str  # 'triggered', 'queued', 'in_progress', 'success', 'failed'
    workflow: str
    workflow_url: Optional[str] = None
    message: str


class BuildProgressMessage(WebSocketMessageBase):
    """Schema for build progress WebSocket messages."""

    type: MessageType = MessageType.BUILD_PROGRESS
    agent: AgentType = AgentType.BUILD_DEPLOY
    stage: str  # 'dependencies', 'build', 'test', 'deploy'
    message: str
    progress: float = Field(..., ge=0.0, le=1.0)


class DeploymentCompleteMessage(WebSocketMessageBase):
    """Schema for deployment complete WebSocket messages."""

    type: MessageType = MessageType.DEPLOYMENT_COMPLETE
    agent: AgentType = AgentType.BUILD_DEPLOY
    status: str  # 'success', 'failed'
    deployment_url: Optional[str] = None
    message: str
    details: Optional[Dict[str, Any]] = None  # build_time, size


class ReviewProgressMessage(WebSocketMessageBase):
    """Schema for code review progress WebSocket messages."""

    type: MessageType = MessageType.REVIEW_PROGRESS
    agent: AgentType = AgentType.CODE_REVIEWER
    file_path: str
    message: str
    progress: float = Field(..., ge=0.0, le=1.0)


class ReviewIssueMessage(WebSocketMessageBase):
    """Schema for code review issue WebSocket messages."""

    type: MessageType = MessageType.REVIEW_ISSUE
    agent: AgentType = AgentType.CODE_REVIEWER
    severity: str  # 'error', 'warning', 'info'
    file_path: str
    line: Optional[int] = None
    message: str


class AgentErrorMessage(WebSocketMessageBase):
    """Schema for agent error WebSocket messages."""

    type: MessageType = MessageType.AGENT_ERROR
    agent: AgentType
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class UserInputRequiredMessage(WebSocketMessageBase):
    """Schema for user input required WebSocket messages."""

    type: MessageType = MessageType.USER_INPUT_REQUIRED
    agent: AgentType
    question: str
    options: Optional[List[str]] = None


class UserMessageWebSocket(WebSocketMessageBase):
    """Schema for user message via WebSocket."""

    type: MessageType = MessageType.USER_MESSAGE
    message: str
    project_id: int


class UserInputResponse(BaseModel):
    """Schema for user input response via WebSocket."""

    type: str = "user_input_response"
    response: str


# Union type for all WebSocket messages
WebSocketMessage = Union[
    AgentStatusMessage,
    ToolExecutionMessage,
    FileOperationMessage,
    GitOperationMessage,
    BuildStatusMessage,
    BuildProgressMessage,
    DeploymentCompleteMessage,
    ReviewProgressMessage,
    ReviewIssueMessage,
    AgentErrorMessage,
    UserInputRequiredMessage,
    UserMessageWebSocket,
]


class PlanStep(BaseModel):
    """Schema for a single step in an execution plan."""

    id: int
    description: str
    agent: AgentType
    status: str = "pending"  # 'pending', 'in_progress', 'completed', 'failed'
    dependencies: List[int] = Field(default_factory=list)
    output: Optional[Dict[str, Any]] = None


class ExecutionPlan(BaseModel):
    """Schema for the complete execution plan."""

    steps: List[PlanStep]
    total_steps: int
    estimated_time_seconds: Optional[int] = None
