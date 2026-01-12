"""Signals package - Event-driven agent activation."""
from app.core.signals.types import Signal, SignalEvent, SignalPriority
from app.core.signals.engine import SignalEngine, get_signal_engine
from app.core.signals.registry import (
    AGENT_SUBSCRIPTIONS,
    AGENT_CAPABILITIES,
    get_agents_for_signal,
    get_signals_for_agent,
    agent_handles_signal,
    get_agent_capabilities,
    get_agents_for_artifact_type,
)

__all__ = [
    # Types
    "Signal",
    "SignalEvent",
    "SignalPriority",
    # Engine
    "SignalEngine",
    "get_signal_engine",
    # Registry
    "AGENT_SUBSCRIPTIONS",
    "AGENT_CAPABILITIES",
    "get_agents_for_signal",
    "get_signals_for_agent",
    "agent_handles_signal",
    "get_agent_capabilities",
    "get_agents_for_artifact_type",
]
