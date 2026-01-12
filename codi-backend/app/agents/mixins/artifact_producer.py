"""Artifact Producer Mixin for agents.

This mixin transforms agents from returning dicts to producing artifacts.
Agents that include this mixin write to the artifact store.
"""
from typing import Any, Dict, List, Optional

from app.core.artifacts import (
    Artifact,
    ArtifactStore,
    ArtifactType,
    get_artifact_store,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ArtifactProducerMixin:
    """
    Mixin for agents that produce artifacts.
    
    This mixin provides methods for creating and persisting artifacts.
    Agents include this mixin to participate in the artifact-centric flow.
    
    Usage:
        class MyAgent(BaseAgent, ArtifactProducerMixin):
            async def run(self, input_data):
                # Do work...
                
                # Produce artifact instead of returning dict
                artifact = await self.produce_file_artifact(
                    file_path="lib/main.dart",
                    content=code,
                    operation="create"
                )
                
                return [artifact]
    """
    
    _artifact_store: Optional[ArtifactStore] = None
    
    @property
    def artifact_store(self) -> ArtifactStore:
        """Get or create artifact store for this agent's project."""
        if self._artifact_store is None:
            # Access context from BaseAgent
            project_id = getattr(self.context, 'project_id', 0)
            project_folder = getattr(self.context, 'project_folder', None)
            
            self._artifact_store = get_artifact_store(
                project_id=project_id,
                project_path=project_folder,
            )
        return self._artifact_store
    
    async def produce_artifact(
        self,
        artifact_type: ArtifactType,
        content: Any,
        metadata: Dict[str, Any] = None,
    ) -> Artifact:
        """
        Produce and persist an artifact.
        
        This is the primary method for agents to output results.
        
        Args:
            artifact_type: Type of artifact
            content: Artifact content
            metadata: Optional metadata
            
        Returns:
            Persisted artifact
        """
        artifact = Artifact(
            type=artifact_type,
            producer=self.name,
            project_id=self.artifact_store.project_id,
            content=content,
            metadata=metadata or {},
        )
        
        await self.artifact_store.persist(artifact)
        
        logger.info(
            f"Agent '{self.name}' produced artifact: "
            f"{artifact.type.value} ({artifact.id[:8]})"
        )
        
        return artifact
    
    async def produce_file_artifact(
        self,
        file_path: str,
        content: str,
        operation: str = "create",
    ) -> Artifact:
        """Produce a file artifact."""
        return await self.produce_artifact(
            artifact_type=ArtifactType.FILE,
            content=content,
            metadata={
                "file_path": file_path,
                "operation": operation,
            },
        )
    
    async def produce_error_artifact(
        self,
        error_message: str,
        error_type: str = "unknown",
        recoverable: bool = True,
        stack_trace: Optional[str] = None,
    ) -> Artifact:
        """Produce an error artifact."""
        return await self.produce_artifact(
            artifact_type=ArtifactType.ERROR,
            content=error_message,
            metadata={
                "error_type": error_type,
                "recoverable": recoverable,
                "stack_trace": stack_trace,
            },
        )
    
    async def produce_build_artifact(
        self,
        success: bool,
        output: str,
        command: str,
        exit_code: int = 0,
    ) -> Artifact:
        """Produce a build artifact."""
        return await self.produce_artifact(
            artifact_type=ArtifactType.BUILD,
            content=output,
            metadata={
                "success": success,
                "command": command,
                "exit_code": exit_code,
            },
        )
    
    async def produce_preview_artifact(
        self,
        url: str,
        container_id: Optional[str] = None,
    ) -> Artifact:
        """Produce a preview artifact."""
        return await self.produce_artifact(
            artifact_type=ArtifactType.PREVIEW,
            content=url,
            metadata={
                "container_id": container_id,
            },
        )
    
    async def produce_analysis_artifact(
        self,
        analysis: Dict[str, Any],
        analysis_type: str = "general",
    ) -> Artifact:
        """Produce an analysis artifact."""
        return await self.produce_artifact(
            artifact_type=ArtifactType.ANALYSIS,
            content=analysis,
            metadata={
                "analysis_type": analysis_type,
            },
        )
    
    async def produce_plan_artifact(
        self,
        plan_content: str,
        title: str,
        status: str = "pending_review",
    ) -> Artifact:
        """Produce a plan artifact."""
        return await self.produce_artifact(
            artifact_type=ArtifactType.PLAN,
            content=plan_content,
            metadata={
                "title": title,
                "status": status,
            },
        )
    
    async def read_artifacts(
        self,
        artifact_type: Optional[ArtifactType] = None,
        limit: int = 100,
    ) -> List[Artifact]:
        """
        Read artifacts from the store.
        
        Args:
            artifact_type: Optional type filter
            limit: Maximum artifacts to return
            
        Returns:
            List of artifacts
        """
        if artifact_type:
            return await self.artifact_store.get_by_type(artifact_type, limit=limit)
        
        # Return all from cache
        return list(self.artifact_store._cache.values())[:limit]
    
    async def get_latest_build(self) -> Optional[Artifact]:
        """Get the latest build artifact."""
        return await self.artifact_store.get_latest(ArtifactType.BUILD)
    
    async def get_preview_url(self) -> Optional[str]:
        """Get the current preview URL."""
        artifact = await self.artifact_store.get_latest(ArtifactType.PREVIEW)
        if artifact:
            return artifact.content
        return None
