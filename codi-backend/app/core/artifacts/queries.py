"""Artifact queries for state-based signal derivation.

These query functions check artifact state to determine what signals
should be emitted. They enable the "reality beats plan" principle.
"""
from typing import List, Optional

from app.core.artifacts.models import Artifact, ArtifactStatus, ArtifactType
from app.core.artifacts.store import ArtifactStore


async def artifact_exists(
    store: ArtifactStore,
    artifact_type: ArtifactType,
    producer: Optional[str] = None,
) -> bool:
    """
    Check if an artifact of a given type exists.
    
    This is the fundamental query for signal derivation:
    
        if not artifact_exists(type="preview_url"):
            emit_signal("NEEDS_PREVIEW")
    
    Args:
        store: Artifact store to query
        artifact_type: Type of artifact to check
        producer: Optional producer to filter by
        
    Returns:
        True if matching artifact exists
    """
    return await store.exists(artifact_type, producer)


async def get_latest_artifact(
    store: ArtifactStore,
    artifact_type: ArtifactType,
    producer: Optional[str] = None,
) -> Optional[Artifact]:
    """
    Get the most recent artifact of a type.
    
    Args:
        store: Artifact store to query
        artifact_type: Type of artifact to get
        producer: Optional producer to filter by
        
    Returns:
        Most recent matching artifact or None
    """
    return await store.get_latest(artifact_type, producer)


async def get_artifacts_by_producer(
    store: ArtifactStore,
    producer: str,
    artifact_type: Optional[ArtifactType] = None,
) -> List[Artifact]:
    """
    Get all artifacts produced by an agent.
    
    Args:
        store: Artifact store to query
        producer: Agent name
        artifact_type: Optional type filter
        
    Returns:
        List of artifacts
    """
    return await store.get_by_producer(producer, artifact_type)


async def has_errors(store: ArtifactStore) -> bool:
    """Check if there are any active error artifacts."""
    return await artifact_exists(store, ArtifactType.ERROR)


async def get_active_errors(store: ArtifactStore) -> List[Artifact]:
    """Get all active error artifacts."""
    return await store.get_by_type(ArtifactType.ERROR, ArtifactStatus.ACTIVE)


async def has_preview(store: ArtifactStore) -> bool:
    """Check if a preview URL artifact exists."""
    return await artifact_exists(store, ArtifactType.PREVIEW)


async def get_preview_url(store: ArtifactStore) -> Optional[str]:
    """Get the current preview URL."""
    artifact = await get_latest_artifact(store, ArtifactType.PREVIEW)
    if artifact and isinstance(artifact.content, str):
        return artifact.content
    return None


async def build_succeeded(store: ArtifactStore) -> bool:
    """Check if the latest build was successful."""
    artifact = await get_latest_artifact(store, ArtifactType.BUILD)
    if artifact:
        return artifact.metadata.get("success", False)
    return False


async def get_file_artifacts(
    store: ArtifactStore,
    file_path: Optional[str] = None,
) -> List[Artifact]:
    """
    Get file artifacts, optionally filtered by path.
    
    Args:
        store: Artifact store to query
        file_path: Optional file path to filter by
        
    Returns:
        List of file artifacts
    """
    artifacts = await store.get_by_type(ArtifactType.FILE, ArtifactStatus.ACTIVE)
    
    if file_path:
        artifacts = [
            a for a in artifacts
            if a.metadata.get("file_path") == file_path
        ]
    
    return artifacts


async def get_pending_plan(store: ArtifactStore) -> Optional[Artifact]:
    """Get any pending implementation plan artifact."""
    artifacts = await store.get_by_type(ArtifactType.PLAN, ArtifactStatus.PENDING)
    return artifacts[0] if artifacts else None


async def count_artifacts_by_type(store: ArtifactStore) -> dict:
    """Get count of artifacts by type."""
    counts = {}
    for artifact_type in ArtifactType:
        artifacts = await store.get_by_type(artifact_type)
        counts[artifact_type.value] = len(artifacts)
    return counts
