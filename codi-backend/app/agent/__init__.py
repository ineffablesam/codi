"""Simple Coding Agent - Baby Code Style.

A simplified agent following the ReAct (Reason, Act, Observe) pattern.
Replaces the complex multi-agent orchestration with a single powerful agent.
"""
from app.agent.agent import CodingAgent, run_agent
from app.agent.tools import TOOLS, execute_tool, AgentContext
from app.agent.executor import execute_code
from app.agent.validator import validate_code

__all__ = [
    "CodingAgent",
    "run_agent",
    "TOOLS",
    "execute_tool",
    "AgentContext",
    "execute_code",
    "validate_code",
]
