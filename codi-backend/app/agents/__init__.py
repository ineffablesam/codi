"""Agents package for LangGraph-based AI agents.

Agent Hierarchy:
- Orchestration: Conductor (master), Strategist, Analyst
- Specialized: Sage, Scholar, Scout, Artisan, Scribe, Vision
- Platform: FlutterEngineer, ReactEngineer, NextjsEngineer, etc.
- Operations: CodeReviewer, GitOperator, BuildDeploy, Memory

Multi-Model Support:
- OpenAI: GPT-5.2 (Sage)
- Anthropic: Claude Opus/Sonnet (Conductor, Scholar, Strategist, Analyst)
- Gemini: Flash/Pro (Scout, Scribe, Vision, Artisan, Platform Engineers)
"""
from app.agents.base import BaseAgent
from app.agents.llm_providers import get_llm, get_llm_for_agent, AGENT_MODEL_CONFIG

# Orchestration agents
from app.agents.orchestration import (
    ConductorAgent,
    StrategistAgent,
    AnalystAgent,
)

# Specialized agents
from app.agents.specialized import (
    SageAgent,
    ScholarAgent,
    ScoutAgent,
    ArtisanAgent,
    ScribeAgent,
    VisionAgent,
    PlannerAgent,
    ImplementationPlannerAgent,
)

# Operations agents
from app.agents.operations import (
    CodeReviewerAgent,
    GitOperatorAgent,
    BuildDeployAgent,
    MemoryAgent,
)

# Platform agents (from subdirectory)
from app.agents.platform import (
    FlutterEngineerAgent,
    ReactEngineerAgent,
    NextjsEngineerAgent,
    ReactNativeEngineerAgent,
    BackendIntegrationAgent,
)

# Core infrastructure
from app.agents.types import (
    TaskStatus,
    BackgroundTask,
    DelegationContext,
    AgentCategory,
    CATEGORIES,
)
from app.agents.background_manager import background_manager, BackgroundManager
from app.agents.session_manager import session_manager, SessionManager

__all__ = [
    # Base
    "BaseAgent",
    # Orchestration
    "ConductorAgent",
    "StrategistAgent",
    "AnalystAgent",
    # Specialized
    "SageAgent",
    "ScholarAgent",
    "ScoutAgent",
    "ArtisanAgent",
    "ScribeAgent",
    "VisionAgent",
    "PlannerAgent",
    "ImplementationPlannerAgent",
    # Operations
    "CodeReviewerAgent",
    "GitOperatorAgent",
    "BuildDeployAgent",
    "MemoryAgent",
    # Platform
    "FlutterEngineerAgent",
    "ReactEngineerAgent",
    "NextjsEngineerAgent",
    "ReactNativeEngineerAgent",
    "BackendIntegrationAgent",
    # Infrastructure
    "TaskStatus",
    "BackgroundTask",
    "DelegationContext",
    "AgentCategory",
    "CATEGORIES",
    "background_manager",
    "BackgroundManager",
    "session_manager",
    "SessionManager",
]
