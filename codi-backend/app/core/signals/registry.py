"""Agent signal subscription registry.

This registry declares which agents subscribe to which signals.
Agents are activated when their subscribed signals fire.
"""
from typing import Dict, List, Set

from app.core.signals.types import Signal


# Static subscription declarations
# Maps agent name to list of signals they handle
AGENT_SUBSCRIPTIONS: Dict[str, List[Signal]] = {
    # Orchestration
    "conductor": [
        Signal.INTENT_PARSED,
        Signal.PLAN_APPROVED,
        Signal.PLAN_REJECTED,
        Signal.ERROR_OCCURRED,
    ],
    
    # Strategy & Analysis
    "analyst": [
        Signal.NEEDS_ANALYSIS,
    ],
    "strategist": [
        # Advisory only, doesn't subscribe to signals
    ],
    
    # Exploration
    "scout": [
        Signal.NEEDS_ANALYSIS,
    ],
    
    # Implementation
    "flutter_engineer": [
        Signal.NEEDS_IMPLEMENTATION,
        Signal.NEEDS_SCAFFOLD,
    ],
    "react_engineer": [
        Signal.NEEDS_IMPLEMENTATION,
        Signal.NEEDS_SCAFFOLD,
    ],
    "nextjs_engineer": [
        Signal.NEEDS_IMPLEMENTATION,
        Signal.NEEDS_SCAFFOLD,
    ],
    "react_native_engineer": [
        Signal.NEEDS_IMPLEMENTATION,
        Signal.NEEDS_SCAFFOLD,
    ],
    
    # UI/UX
    "artisan": [
        Signal.NEEDS_UI_DESIGN,
        Signal.NEEDS_UI_POLISH,
    ],
    
    # Fixing / Stabilization
    "sage": [
        Signal.ERROR_OCCURRED,
        Signal.BUILD_FAILED,
        Signal.TESTS_FAILING,
    ],
    
    # Git / Persistence
    "git_operator": [
        Signal.NEEDS_COMMIT,
        Signal.NEEDS_PUSH,
        Signal.DIRTY_GIT_STATE,
    ],
    
    # Build / Deploy
    "build_deploy": [
        Signal.NEEDS_BUILD,
        Signal.NEEDS_PREVIEW,
        Signal.PREVIEW_STALE,
    ],
    
    # Review
    "code_reviewer": [
        Signal.CODE_REVIEW_NEEDED,
    ],
    
    # Documentation
    "scribe": [
        # Doesn't subscribe - invoked explicitly
    ],
    
    # Planning
    "implementation_planner": [
        Signal.PLAN_APPROVED,
    ],
}


def get_agents_for_signal(signal: Signal) -> List[str]:
    """Get all agents that subscribe to a signal."""
    agents = []
    for agent, signals in AGENT_SUBSCRIPTIONS.items():
        if signal in signals:
            agents.append(agent)
    return agents


def get_signals_for_agent(agent: str) -> List[Signal]:
    """Get all signals an agent subscribes to."""
    return AGENT_SUBSCRIPTIONS.get(agent, [])


def agent_handles_signal(agent: str, signal: Signal) -> bool:
    """Check if an agent handles a signal."""
    return signal in AGENT_SUBSCRIPTIONS.get(agent, [])


# Capability mapping - what can each agent produce as artifacts
AGENT_CAPABILITIES: Dict[str, Set[str]] = {
    "conductor": {"plan", "intent"},
    "analyst": {"analysis", "intent"},
    "scout": {"analysis"},
    "flutter_engineer": {"file", "diff"},
    "react_engineer": {"file", "diff"},
    "nextjs_engineer": {"file", "diff"},
    "react_native_engineer": {"file", "diff"},
    "artisan": {"file", "diff"},
    "sage": {"file", "diff", "analysis"},
    "git_operator": {"log"},
    "build_deploy": {"build", "preview"},
    "code_reviewer": {"analysis"},
    "scribe": {"file"},
    "implementation_planner": {"plan"},
}


def get_agent_capabilities(agent: str) -> Set[str]:
    """Get artifact types an agent can produce."""
    return AGENT_CAPABILITIES.get(agent, set())


def get_agents_for_artifact_type(artifact_type: str) -> List[str]:
    """Get agents that can produce an artifact type."""
    agents = []
    for agent, capabilities in AGENT_CAPABILITIES.items():
        if artifact_type in capabilities:
            agents.append(agent)
    return agents
