"""Artifact models and types for the Antigravity architecture.

Artifacts are first-class objects that agents produce. Agents don't "return results" -
they write artifacts. Other agents read artifacts. This is the core abstraction.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
import hashlib
import json
import uuid


class ArtifactType(str, Enum):
    """Types of artifacts that agents can produce."""
    
    # File system artifacts
    FILE = "file"           # Created/modified file
    DIFF = "diff"           # Code diff/patch
    
    # Build artifacts
    BUILD = "build"         # Build result (success/failure)
    PREVIEW = "preview"     # Preview URL
    
    # State artifacts
    ERROR = "error"         # Error condition
    LOG = "log"             # Log entry
    
    # Planning artifacts
    PLAN = "plan"           # Implementation plan
    TASK = "task"           # Task completion
    
    # Analysis artifacts
    ANALYSIS = "analysis"   # Code analysis result
    INTENT = "intent"       # Parsed user intent


class ArtifactStatus(str, Enum):
    """Status of an artifact."""
    
    PENDING = "pending"       # Not yet processed
    ACTIVE = "active"         # Current/valid artifact
    SUPERSEDED = "superseded" # Replaced by newer artifact
    INVALID = "invalid"       # Failed validation


@dataclass
class Artifact:
    """
    Core artifact abstraction.
    
    Artifacts are immutable records of agent outputs. They form the shared
    state space that agents read from and write to.
    
    Principles:
    - Agents write artifacts, never talk to other agents directly
    - Artifacts are immutable once created
    - Artifact state drives signals
    - Multiple artifacts of same type can coexist (versioning)
    """
    
    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: ArtifactType = ArtifactType.LOG
    
    # Producer
    producer: str = ""  # Agent name that created this
    project_id: int = 0
    
    # Content
    content: Any = None  # The actual artifact content
    content_hash: str = ""  # SHA256 of content for dedup
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ArtifactStatus = ArtifactStatus.ACTIVE
    
    # Relationships
    parent_id: Optional[str] = None  # Previous version
    related_ids: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Compute content hash if not provided."""
        if not self.content_hash and self.content is not None:
            self.content_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """Compute SHA256 hash of content."""
        if isinstance(self.content, str):
            data = self.content.encode()
        elif isinstance(self.content, bytes):
            data = self.content
        else:
            data = json.dumps(self.content, sort_keys=True, default=str).encode()
        return hashlib.sha256(data).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert artifact to dictionary for serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "producer": self.producer,
            "project_id": self.project_id,
            "content": self.content,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "related_ids": self.related_ids,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        """Create artifact from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=ArtifactType(data.get("type", "log")),
            producer=data.get("producer", ""),
            project_id=data.get("project_id", 0),
            content=data.get("content"),
            content_hash=data.get("content_hash", ""),
            metadata=data.get("metadata", {}),
            status=ArtifactStatus(data.get("status", "active")),
            parent_id=data.get("parent_id"),
            related_ids=data.get("related_ids", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
        )
    
    def supersede(self, new_content: Any, metadata: Dict[str, Any] = None) -> "Artifact":
        """Create a new artifact that supersedes this one."""
        self.status = ArtifactStatus.SUPERSEDED
        return Artifact(
            type=self.type,
            producer=self.producer,
            project_id=self.project_id,
            content=new_content,
            metadata={**self.metadata, **(metadata or {})},
            parent_id=self.id,
            related_ids=[self.id] + self.related_ids,
        )


@dataclass
class FileArtifact(Artifact):
    """Specialized artifact for file operations."""
    
    type: ArtifactType = ArtifactType.FILE
    
    @property
    def file_path(self) -> Optional[str]:
        return self.metadata.get("file_path")
    
    @property
    def operation(self) -> Optional[str]:
        """create, update, delete"""
        return self.metadata.get("operation")


@dataclass
class ErrorArtifact(Artifact):
    """Specialized artifact for error conditions."""
    
    type: ArtifactType = ArtifactType.ERROR
    
    @property
    def error_type(self) -> Optional[str]:
        return self.metadata.get("error_type")
    
    @property
    def stack_trace(self) -> Optional[str]:
        return self.metadata.get("stack_trace")
    
    @property
    def recoverable(self) -> bool:
        return self.metadata.get("recoverable", True)


@dataclass 
class BuildArtifact(Artifact):
    """Specialized artifact for build results."""
    
    type: ArtifactType = ArtifactType.BUILD
    
    @property
    def success(self) -> bool:
        return self.metadata.get("success", False)
    
    @property
    def command(self) -> Optional[str]:
        return self.metadata.get("command")
    
    @property
    def exit_code(self) -> Optional[int]:
        return self.metadata.get("exit_code")


@dataclass
class PreviewArtifact(Artifact):
    """Specialized artifact for preview URLs."""
    
    type: ArtifactType = ArtifactType.PREVIEW
    
    @property
    def url(self) -> Optional[str]:
        return self.content if isinstance(self.content, str) else None
    
    @property
    def container_id(self) -> Optional[str]:
        return self.metadata.get("container_id")
