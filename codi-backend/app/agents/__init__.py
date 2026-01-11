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
from app.agents.planner import PlannerAgent
from app.agents.code_reviewer import CodeReviewerAgent
from app.agents.git_operator import GitOperatorAgent
from app.agents.build_deploy import BuildDeployAgent
from app.agents.memory import MemoryAgent

# Orchestration agents
from app.agents.conductor import ConductorAgent
from app.agents.strategist import StrategistAgent
from app.agents.analyst import AnalystAgent

# Specialized agents
from app.agents.sage import SageAgent
from app.agents.scholar import ScholarAgent
from app.agents.scout import ScoutAgent
from app.agents.artisan import ArtisanAgent
from app.agents.scribe import ScribeAgent
from app.agents.vision import VisionAgent

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
    # Operations
    "PlannerAgent",
    "CodeReviewerAgent",
    "GitOperatorAgent",
    "BuildDeployAgent",
    "MemoryAgent",
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
