"""Workflows package - simplified agent execution.

This package now uses the simple baby-code style agent instead of
the complex LangGraph workflow graph.
"""
from app.workflows.executor import WorkflowExecutor, run_workflow

__all__ = [
    "WorkflowExecutor",
    "run_workflow",
]
