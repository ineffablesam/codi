"""Types for the Codi multi-agent orchestration system."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """Status of a background task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCategory(str, Enum):
    """Categories for agent task routing."""
    VISUAL = "visual"       # UI/UX, frontend design
    LOGIC = "logic"         # Backend, business logic
    MOBILE = "mobile"       # Flutter, React Native
    GENERAL = "general"     # Default category


@dataclass
class TaskProgress:
    """Progress tracking for background tasks."""
    tool_calls: int = 0
    last_tool: Optional[str] = None
    last_update: datetime = field(default_factory=datetime.utcnow)
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None


@dataclass
class BackgroundTask:
    """A background task managed by the BackgroundManager."""
    id: str
    session_id: str
    parent_session_id: str
    description: str
    prompt: str
    agent: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[str] = None
    progress: TaskProgress = field(default_factory=TaskProgress)
    
    # Parent context for notifications
    parent_agent: Optional[str] = None
    parent_model: Optional[str] = None
    
    # Concurrency control
    concurrency_key: Optional[str] = None
    
    # Category/skill metadata
    category: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "parent_session_id": self.parent_session_id,
            "description": self.description,
            "agent": self.agent,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "category": self.category,
            "progress": {
                "tool_calls": self.progress.tool_calls,
                "last_tool": self.progress.last_tool,
                "last_update": self.progress.last_update.isoformat(),
            }
        }


@dataclass
class LaunchInput:
    """Input for launching a new background task."""
    description: str
    prompt: str
    agent: str
    parent_session_id: str
    parent_message_id: Optional[str] = None
    parent_agent: Optional[str] = None
    parent_model: Optional[str] = None
    category: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    skill_content: Optional[str] = None


@dataclass
class ResumeInput:
    """Input for resuming an existing task."""
    session_id: str
    prompt: str
    parent_session_id: str
    parent_message_id: Optional[str] = None
    parent_agent: Optional[str] = None
    parent_model: Optional[str] = None


@dataclass
class DelegationContext:
    """Context for agent delegation."""
    from_agent: str
    to_agent: str
    category: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    reason: str = ""
    expected_outcome: str = ""


# Category configurations matching reference implementation
# NOTE: Gemini 3 recommends temperature=1.0 (lower values may cause looping)
CATEGORIES = {
    "visual": {
        "model_key": "artisan_model",
        "fallback_model": "gemini-3-flash-preview",
        "temperature": 1.0,  # Gemini 3 default - do NOT lower
        "description": "Frontend/UI specialist"
    },
    "logic": {
        "model_key": "sage_model",
        "fallback_model": "gemini-3-pro-preview",
        "temperature": 1.0,  # Gemini 3 default - do NOT lower
        "description": "Backend logic specialist"
    },
    "mobile": {
        "model_key": "artisan_model",
        "fallback_model": "gemini-3-flash-preview",
        "temperature": 1.0,  # Gemini 3 default - do NOT lower
        "description": "Flutter/React Native specialist"
    },
    "general": {
        "model_key": "gemini_model",
        "fallback_model": "gemini-3-flash-preview",
        "temperature": 1.0,  # Gemini 3 default - do NOT lower
        "description": "General purpose tasks"
    }
}
