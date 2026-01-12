"""Artifact store with hybrid Git+DB+FS storage.

Storage strategy:
- Git: Source of truth for file artifacts (committed to repo)
- DB: Metadata, queries, relationships
- FS: Execution cache, temporary artifacts

The store provides a unified interface for artifact CRUD operations.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.artifacts.models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    FileArtifact,
    ErrorArtifact,
    BuildArtifact,
    PreviewArtifact,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ArtifactStore:
    """
    Hybrid artifact store with Git+DB+FS backing.
    
    This is the single source of truth for all artifacts in a project.
    Agents write artifacts here, and read artifacts from here.
    """
    
    def __init__(
        self,
        project_id: int,
        project_path: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ):
        """
        Initialize artifact store.
        
        Args:
            project_id: Project ID for scoping artifacts
            project_path: Local filesystem path for the project
            db: Optional database session for metadata persistence
        """
        self.project_id = project_id
        self.project_path = Path(project_path) if project_path else None
        self.db = db
        
        # In-memory cache for current session
        self._cache: Dict[str, Artifact] = {}
        
        # .codi directory for persistent artifacts
        if self.project_path:
            self._codi_dir = self.project_path / ".codi"
            self._artifacts_dir = self._codi_dir / "artifacts"
        else:
            self._codi_dir = None
            self._artifacts_dir = None
    
    async def persist(self, artifact: Artifact) -> Artifact:
        """
        Persist an artifact to storage.
        
        Args:
            artifact: Artifact to persist
            
        Returns:
            Persisted artifact with updated metadata
        """
        # Set project ID if not set
        if not artifact.project_id:
            artifact.project_id = self.project_id
        
        # Add to cache
        self._cache[artifact.id] = artifact
        
        # Persist to filesystem for file artifacts
        if artifact.type == ArtifactType.FILE and self._artifacts_dir:
            await self._persist_to_fs(artifact)
        
        # Persist metadata to database if available
        if self.db:
            await self._persist_to_db(artifact)
        
        logger.debug(f"Persisted artifact {artifact.id} ({artifact.type.value})")
        return artifact
    
    async def persist_batch(self, artifacts: List[Artifact]) -> List[Artifact]:
        """Persist multiple artifacts."""
        return [await self.persist(a) for a in artifacts]
    
    async def get(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID."""
        # Check cache first
        if artifact_id in self._cache:
            return self._cache[artifact_id]
        
        # Try filesystem
        if self._artifacts_dir:
            artifact = await self._load_from_fs(artifact_id)
            if artifact:
                self._cache[artifact_id] = artifact
                return artifact
        
        # Try database
        if self.db:
            artifact = await self._load_from_db(artifact_id)
            if artifact:
                self._cache[artifact_id] = artifact
                return artifact
        
        return None
    
    async def get_by_type(
        self,
        artifact_type: ArtifactType,
        status: Optional[ArtifactStatus] = None,
        limit: int = 100,
    ) -> List[Artifact]:
        """Get artifacts by type."""
        results = []
        
        for artifact in self._cache.values():
            if artifact.type == artifact_type:
                if status is None or artifact.status == status:
                    results.append(artifact)
        
        # Sort by created_at descending
        results.sort(key=lambda a: a.created_at, reverse=True)
        return results[:limit]
    
    async def get_by_producer(
        self,
        producer: str,
        artifact_type: Optional[ArtifactType] = None,
        limit: int = 100,
    ) -> List[Artifact]:
        """Get artifacts by producer agent."""
        results = []
        
        for artifact in self._cache.values():
            if artifact.producer == producer:
                if artifact_type is None or artifact.type == artifact_type:
                    results.append(artifact)
        
        results.sort(key=lambda a: a.created_at, reverse=True)
        return results[:limit]
    
    async def get_latest(
        self,
        artifact_type: ArtifactType,
        producer: Optional[str] = None,
    ) -> Optional[Artifact]:
        """Get the most recent artifact of a type."""
        artifacts = await self.get_by_type(artifact_type, ArtifactStatus.ACTIVE, limit=1)
        
        if producer:
            artifacts = [a for a in artifacts if a.producer == producer]
        
        return artifacts[0] if artifacts else None
    
    async def exists(
        self,
        artifact_type: ArtifactType,
        producer: Optional[str] = None,
        status: ArtifactStatus = ArtifactStatus.ACTIVE,
    ) -> bool:
        """Check if an artifact exists matching criteria."""
        artifacts = await self.get_by_type(artifact_type, status, limit=1)
        
        if producer:
            artifacts = [a for a in artifacts if a.producer == producer]
        
        return len(artifacts) > 0
    
    async def supersede(
        self,
        artifact_id: str,
        new_content: Any,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Artifact]:
        """Create a new artifact that supersedes an existing one."""
        old_artifact = await self.get(artifact_id)
        if not old_artifact:
            return None
        
        new_artifact = old_artifact.supersede(new_content, metadata)
        await self.persist(old_artifact)  # Save the superseded status
        await self.persist(new_artifact)
        
        return new_artifact
    
    async def invalidate(self, artifact_id: str) -> bool:
        """Mark an artifact as invalid."""
        artifact = await self.get(artifact_id)
        if not artifact:
            return False
        
        artifact.status = ArtifactStatus.INVALID
        await self.persist(artifact)
        return True
    
    # Filesystem operations
    async def _persist_to_fs(self, artifact: Artifact) -> None:
        """Persist artifact to filesystem."""
        if not self._artifacts_dir:
            return
        
        self._artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_file = self._artifacts_dir / f"{artifact.id}.json"
        artifact_file.write_text(
            json.dumps(artifact.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
    
    async def _load_from_fs(self, artifact_id: str) -> Optional[Artifact]:
        """Load artifact from filesystem."""
        if not self._artifacts_dir:
            return None
        
        artifact_file = self._artifacts_dir / f"{artifact_id}.json"
        if not artifact_file.exists():
            return None
        
        try:
            data = json.loads(artifact_file.read_text(encoding="utf-8"))
            return Artifact.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load artifact from FS: {e}")
            return None
    
    # Database operations (placeholder - will use SQLAlchemy model)
    async def _persist_to_db(self, artifact: Artifact) -> None:
        """Persist artifact metadata to database."""
        # Will be implemented when we add the SQLAlchemy model
        pass
    
    async def _load_from_db(self, artifact_id: str) -> Optional[Artifact]:
        """Load artifact from database."""
        # Will be implemented when we add the SQLAlchemy model
        return None
    
    # Convenience factory methods
    def create_file_artifact(
        self,
        producer: str,
        file_path: str,
        content: str,
        operation: str = "create",
    ) -> FileArtifact:
        """Create a file artifact."""
        return FileArtifact(
            producer=producer,
            project_id=self.project_id,
            content=content,
            metadata={
                "file_path": file_path,
                "operation": operation,
            },
        )
    
    def create_error_artifact(
        self,
        producer: str,
        error_message: str,
        error_type: str = "unknown",
        stack_trace: Optional[str] = None,
        recoverable: bool = True,
    ) -> ErrorArtifact:
        """Create an error artifact."""
        return ErrorArtifact(
            producer=producer,
            project_id=self.project_id,
            content=error_message,
            metadata={
                "error_type": error_type,
                "stack_trace": stack_trace,
                "recoverable": recoverable,
            },
        )
    
    def create_build_artifact(
        self,
        producer: str,
        success: bool,
        output: str,
        command: str,
        exit_code: int = 0,
    ) -> BuildArtifact:
        """Create a build artifact."""
        return BuildArtifact(
            producer=producer,
            project_id=self.project_id,
            content=output,
            metadata={
                "success": success,
                "command": command,
                "exit_code": exit_code,
            },
        )
    
    def create_preview_artifact(
        self,
        producer: str,
        url: str,
        container_id: Optional[str] = None,
    ) -> PreviewArtifact:
        """Create a preview artifact."""
        return PreviewArtifact(
            producer=producer,
            project_id=self.project_id,
            content=url,
            metadata={
                "container_id": container_id,
            },
        )


# Singleton store registry (per project)
_stores: Dict[int, ArtifactStore] = {}


def get_artifact_store(
    project_id: int,
    project_path: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> ArtifactStore:
    """Get or create artifact store for a project."""
    if project_id not in _stores:
        _stores[project_id] = ArtifactStore(
            project_id=project_id,
            project_path=project_path,
            db=db,
        )
    return _stores[project_id]
