"""Browser Agent - Gemini 2.5 Computer Use.

This module re-exports the ComputerUseAgent for backward compatibility.
All legacy code has been removed - uses only the new Computer Use API.
"""
from app.agent.computer_use_agent import (
    ComputerUseAgent,
    run_computer_use_agent,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)

# Re-export for compatibility
BrowserAgent = ComputerUseAgent
run_browser_agent = run_computer_use_agent

__all__ = [
    "BrowserAgent",
    "ComputerUseAgent", 
    "run_browser_agent",
    "run_computer_use_agent",
    "SCREEN_WIDTH",
    "SCREEN_HEIGHT",
]
