"""Agent and WebSocket message Pydantic schemas - Simplified."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    STARTED = "started"
    THINKING = "thinking"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageType(str, Enum):
    """WebSocket message type enumeration."""

    AGENT_STATUS = "agent_status"
    AGENT_RESPONSE = "agent_response"
    TOOL_EXECUTION = "tool_execution"
    FILE_OPERATION = "file_operation"
    GIT_OPERATION = "git_operation"
    BUILD_PROGRESS = "build_progress"
    DEPLOYMENT_COMPLETE = "deployment_complete"
    AGENT_ERROR = "agent_error"
    CONVERSATIONAL_RESPONSE = "conversational_response"
    USER_MESSAGE = "user_message"
    PING = "ping"
    PONG = "pong"


class AgentTaskRequest(BaseModel):
    """Schema for submitting a task to the agent."""

    message: str = Field(..., min_length=1, max_length=10000)
    project_id: int


class AgentTaskResponse(BaseModel):
    """Schema for agent task submission response."""

    task_id: str
    status: str = "queued"
    message: str = "Task submitted successfully"
    created_at: Optional[datetime] = None


class AgentTaskStatus(BaseModel):
    """Schema for agent task status."""

    task_id: str
    status: str  # 'queued', 'processing', 'completed', 'failed'
    progress: Optional[float] = None
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
    agent: str = "codi"
    status: AgentStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class ToolExecutionMessage(WebSocketMessageBase):
    """Schema for tool execution WebSocket messages."""

    type: MessageType = MessageType.TOOL_EXECUTION
    agent: str = "codi"
    tool: str
    message: str


class FileOperationMessage(WebSocketMessageBase):
    """Schema for file operation WebSocket messages."""

    type: MessageType = MessageType.FILE_OPERATION
    agent: str = "codi"
    operation: str  # 'create', 'update', 'delete'
    file_path: str
    message: str
    stats: Optional[str] = None


class GitOperationMessage(WebSocketMessageBase):
    """Schema for git operation WebSocket messages."""

    type: MessageType = MessageType.GIT_OPERATION
    agent: str = "codi"
    operation: str  # 'commit'
    branch_name: Optional[str] = None
    commit_sha: Optional[str] = None
    message: str


class BuildProgressMessage(WebSocketMessageBase):
    """Schema for build progress WebSocket messages."""

    type: MessageType = MessageType.BUILD_PROGRESS
    agent: str = "codi"
    stage: str
    message: str
    progress: float = Field(..., ge=0.0, le=1.0)


class DeploymentCompleteMessage(WebSocketMessageBase):
    """Schema for deployment complete WebSocket messages."""

    type: MessageType = MessageType.DEPLOYMENT_COMPLETE
    agent: str = "codi"
    status: str  # 'success', 'failed'
    deployment_url: Optional[str] = None
    message: str


class AgentErrorMessage(WebSocketMessageBase):
    """Schema for agent error WebSocket messages."""

    type: MessageType = MessageType.AGENT_ERROR
    agent: str = "codi"
    error: str
    message: str


class AgentResponseMessage(WebSocketMessageBase):
    """Schema for final agent response."""

    type: MessageType = MessageType.AGENT_RESPONSE
    message: str


class ConversationalResponseMessage(WebSocketMessageBase):
    """Schema for conversational (non-task) responses."""

    type: MessageType = MessageType.CONVERSATIONAL_RESPONSE
    message: str
    needs_clarification: Optional[bool] = None


class UserMessageWebSocket(WebSocketMessageBase):
    """Schema for user message via WebSocket."""

    type: MessageType = MessageType.USER_MESSAGE
    message: str
    project_id: int


# Union type for all WebSocket messages
WebSocketMessage = Union[
    AgentStatusMessage,
    ToolExecutionMessage,
    FileOperationMessage,
    GitOperationMessage,
    BuildProgressMessage,
    DeploymentCompleteMessage,
    AgentErrorMessage,
    AgentResponseMessage,
    ConversationalResponseMessage,
    UserMessageWebSocket,
]
