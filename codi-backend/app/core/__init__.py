"""Core infrastructure package for Codi backend.

This package provides:
- config: Application settings
- database: SQLAlchemy database connection
- artifacts: Antigravity artifact storage
- signals: Event-driven agent activation
- attractors: Stable state definitions
"""
from app.core.config import settings
from app.core.database import init_db, get_db, get_db_context, Base

# Antigravity core
from app.core.artifacts import Artifact, ArtifactType, ArtifactStore, get_artifact_store
from app.core.signals import Signal, SignalEngine, get_signal_engine
from app.core.attractors import Attractor, AttractorEvaluator

__all__ = [
    # Config
    "settings",
    # Database
    "init_db",
    "get_db",
    "get_db_context",
    "Base",
    # Artifacts
    "Artifact",
    "ArtifactType", 
    "ArtifactStore",
    "get_artifact_store",
    # Signals
    "Signal",
    "SignalEngine",
    "get_signal_engine",
    # Attractors
    "Attractor",
    "AttractorEvaluator",
]
