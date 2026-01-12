"""Artifacts package - First-class artifact storage and queries."""
from app.core.artifacts.models import (
    Artifact,
    ArtifactType,
    ArtifactStatus,
    FileArtifact,
    ErrorArtifact,
    BuildArtifact,
    PreviewArtifact,
)
from app.core.artifacts.store import ArtifactStore, get_artifact_store
from app.core.artifacts.queries import (
    artifact_exists,
    get_latest_artifact,
    get_artifacts_by_producer,
    has_errors,
    get_active_errors,
    has_preview,
    get_preview_url,
    build_succeeded,
    get_file_artifacts,
    get_pending_plan,
    count_artifacts_by_type,
)

__all__ = [
    # Models
    "Artifact",
    "ArtifactType",
    "ArtifactStatus",
    "FileArtifact",
    "ErrorArtifact",
    "BuildArtifact",
    "PreviewArtifact",
    # Store
    "ArtifactStore",
    "get_artifact_store",
    # Queries
    "artifact_exists",
    "get_latest_artifact",
    "get_artifacts_by_producer",
    "has_errors",
    "get_active_errors",
    "has_preview",
    "get_preview_url",
    "build_succeeded",
    "get_file_artifacts",
    "get_pending_plan",
    "count_artifacts_by_type",
]
