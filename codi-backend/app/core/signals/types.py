"""Signal types for event-driven agent activation.

Signals are derived from artifact state and drive agent activation.
Agents subscribe to signals, not tasks.

Key principle: Signals replace explicit delegation.
    
    # OLD: Explicit delegation
    delegate_task(agent="build_deploy", task="build project")
    
    # NEW: Signal-based
    emit_signal(Signal.NEEDS_BUILD)  # Any capable agent wakes up
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class Signal(str, Enum):
    """
    System signals that drive agent activation.
    
    Signals are derived from artifact state. When an attractor is not satisfied,
    the system emits signals that agents can subscribe to.
    """
    
    # Build/Preview signals
    NEEDS_SCAFFOLD = "needs_scaffold"       # Project needs initial setup
    NEEDS_BUILD = "needs_build"             # Project needs to be built
    BUILD_FAILED = "build_failed"           # Build failed, needs fix
    NEEDS_PREVIEW = "needs_preview"         # No preview URL available
    PREVIEW_STALE = "preview_stale"         # Preview needs refresh
    
    # Code signals
    NEEDS_IMPLEMENTATION = "needs_implementation"  # Code needs to be written
    CODE_REVIEW_NEEDED = "code_review_needed"      # Code needs review
    TESTS_FAILING = "tests_failing"                # Tests need fix
    
    # Git signals
    DIRTY_GIT_STATE = "dirty_git_state"     # Uncommitted changes
    NEEDS_COMMIT = "needs_commit"           # Changes ready to commit
    NEEDS_PUSH = "needs_push"               # Commits ready to push
    
    # Planning signals
    PLAN_APPROVED = "plan_approved"         # Plan was approved
    PLAN_REJECTED = "plan_rejected"         # Plan was rejected
    TASK_COMPLETE = "task_complete"         # A task completed
    
    # Error signals
    ERROR_OCCURRED = "error_occurred"       # Error needs handling
    ERROR_RESOLVED = "error_resolved"       # Error was fixed
    
    # Analysis signals
    NEEDS_ANALYSIS = "needs_analysis"       # Code needs analysis
    INTENT_PARSED = "intent_parsed"         # User intent was parsed
    
    # UI signals
    NEEDS_UI_DESIGN = "needs_ui_design"     # UI needs design
    NEEDS_UI_POLISH = "needs_ui_polish"     # UI needs polish


class SignalPriority(str, Enum):
    """Priority levels for signals."""
    
    CRITICAL = "critical"   # Must be handled immediately
    HIGH = "high"           # Handle soon
    NORMAL = "normal"       # Standard priority
    LOW = "low"             # Handle when convenient


@dataclass
class SignalEvent:
    """
    An emitted signal with context.
    
    SignalEvents are the actual emissions that agents receive.
    They carry the signal type plus contextual information.
    """
    
    signal: Signal
    project_id: int
    
    # Context for the signal
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Source of the signal
    source: str = "system"  # Agent name or "system"
    
    # Priority
    priority: SignalPriority = SignalPriority.NORMAL
    
    # Related artifact IDs
    artifact_ids: list = field(default_factory=list)
    
    # Timestamp
    emitted_at: datetime = field(default_factory=datetime.utcnow)
    
    # Optional correlation ID for tracing
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "signal": self.signal.value,
            "project_id": self.project_id,
            "context": self.context,
            "source": self.source,
            "priority": self.priority.value,
            "artifact_ids": self.artifact_ids,
            "emitted_at": self.emitted_at.isoformat(),
            "correlation_id": self.correlation_id,
        }


# Signal to attractor mapping
# Which signals are emitted when attractors are not satisfied
SIGNAL_TO_ATTRACTOR = {
    Signal.NEEDS_BUILD: "project_builds",
    Signal.BUILD_FAILED: "project_builds",
    Signal.NEEDS_PREVIEW: "preview_available",
    Signal.ERROR_OCCURRED: "no_errors",
    Signal.DIRTY_GIT_STATE: "git_clean",
}


# Signal compatibility - which signals can coexist
INCOMPATIBLE_SIGNALS = {
    Signal.ERROR_RESOLVED: {Signal.ERROR_OCCURRED},
    Signal.PLAN_APPROVED: {Signal.PLAN_REJECTED},
    Signal.PLAN_REJECTED: {Signal.PLAN_APPROVED},
}
