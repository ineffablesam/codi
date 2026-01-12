"""Attractor definitions - Stable states the system converges to.

Attractors are the goal states that Codi continuously works toward.
The system runs until all attractors are satisfied (or timeout).

Key principle: Attractors are evaluated from artifact state.
When an attractor is not satisfied, signals are derived and emitted.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.core.artifacts import ArtifactStore, ArtifactType
from app.core.signals.types import Signal


class AttractorStatus(str, Enum):
    """Status of an attractor."""
    
    SATISFIED = "satisfied"       # Attractor is met
    UNSATISFIED = "unsatisfied"   # Working toward it
    BLOCKED = "blocked"           # Can't proceed (error)


@dataclass
class Attractor:
    """
    A stable state definition.
    
    Attractors define what "done" looks like. The system continuously
    evaluates attractors and works to satisfy them.
    """
    
    name: str
    description: str
    
    # Function to evaluate if attractor is satisfied
    # Takes ArtifactStore, returns bool
    evaluator: Callable[[ArtifactStore], bool] = None
    
    # Signal to emit when unsatisfied
    signal_on_unsatisfied: Optional[Signal] = None
    
    # Priority (higher = more important)
    priority: int = 0
    
    # Dependencies - other attractors that must be satisfied first
    depends_on: List[str] = field(default_factory=list)
    
    # Whether this is a terminal attractor (system stops when reached)
    terminal: bool = False


# Core attractor evaluator functions
async def _project_builds(store: ArtifactStore) -> bool:
    """Check if project builds successfully."""
    from app.core.artifacts import build_succeeded
    return await build_succeeded(store)


async def _preview_available(store: ArtifactStore) -> bool:
    """Check if preview URL is available."""
    from app.core.artifacts import has_preview
    return await has_preview(store)


async def _no_errors(store: ArtifactStore) -> bool:
    """Check if there are no active errors."""
    from app.core.artifacts import has_errors
    return not await has_errors(store)


async def _git_clean(store: ArtifactStore) -> bool:
    """Check if git state is clean (no uncommitted changes)."""
    # For now, check if there are file artifacts that haven't been committed
    from app.core.artifacts import get_file_artifacts
    files = await get_file_artifacts(store)
    # If no file artifacts pending, git is clean
    # This will be enhanced with actual git status checking
    return len(files) == 0


async def _has_scaffold(store: ArtifactStore) -> bool:
    """Check if project has been scaffolded."""
    # Check for presence of key project files
    from app.core.artifacts import get_file_artifacts
    files = await get_file_artifacts(store)
    # Basic check - if we have any files, scaffold exists
    # Can be enhanced to check for specific framework files
    return len(files) > 0


async def _plan_approved(store: ArtifactStore) -> bool:
    """Check if there's an approved plan."""
    from app.core.artifacts import get_latest_artifact
    plan = await get_latest_artifact(store, ArtifactType.PLAN)
    if plan:
        return plan.metadata.get("status") == "approved"
    return True  # No plan needed = satisfied


async def _tests_passing(store: ArtifactStore) -> bool:
    """Check if all tests are passing."""
    # Check latest build artifact for test results
    from app.core.artifacts import get_latest_artifact
    build = await get_latest_artifact(store, ArtifactType.BUILD)
    if build:
        return build.metadata.get("tests_passed", True)
    return True  # No tests = passing


# Core attractor definitions
ATTRACTORS: Dict[str, Attractor] = {
    "project_builds": Attractor(
        name="project_builds",
        description="Project builds successfully without errors",
        evaluator=_project_builds,
        signal_on_unsatisfied=Signal.NEEDS_BUILD,
        priority=10,
    ),
    
    "preview_available": Attractor(
        name="preview_available",
        description="A preview URL is available for the project",
        evaluator=_preview_available,
        signal_on_unsatisfied=Signal.NEEDS_PREVIEW,
        priority=5,
        depends_on=["project_builds"],
    ),
    
    "no_errors": Attractor(
        name="no_errors",
        description="No active error conditions exist",
        evaluator=_no_errors,
        signal_on_unsatisfied=Signal.ERROR_OCCURRED,
        priority=20,
    ),
    
    "git_clean": Attractor(
        name="git_clean",
        description="All changes are committed to git",
        evaluator=_git_clean,
        signal_on_unsatisfied=Signal.DIRTY_GIT_STATE,
        priority=3,
    ),
    
    "has_scaffold": Attractor(
        name="has_scaffold",
        description="Project has been scaffolded with initial files",
        evaluator=_has_scaffold,
        signal_on_unsatisfied=Signal.NEEDS_SCAFFOLD,
        priority=15,
    ),
    
    "plan_approved": Attractor(
        name="plan_approved",
        description="Implementation plan has been approved (if needed)",
        evaluator=_plan_approved,
        signal_on_unsatisfied=None,  # Requires user action
        priority=25,
    ),
    
    "tests_passing": Attractor(
        name="tests_passing",
        description="All tests are passing",
        evaluator=_tests_passing,
        signal_on_unsatisfied=Signal.TESTS_FAILING,
        priority=8,
        depends_on=["project_builds"],
    ),
}


def get_attractor(name: str) -> Optional[Attractor]:
    """Get an attractor by name."""
    return ATTRACTORS.get(name)


def get_all_attractors() -> List[Attractor]:
    """Get all attractors sorted by priority."""
    return sorted(ATTRACTORS.values(), key=lambda a: -a.priority)


def get_signals_for_unsatisfied(attractor_name: str) -> Optional[Signal]:
    """Get the signal to emit when an attractor is unsatisfied."""
    attractor = ATTRACTORS.get(attractor_name)
    return attractor.signal_on_unsatisfied if attractor else None
