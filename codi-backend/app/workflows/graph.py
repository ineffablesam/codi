"""LangGraph workflow graph definition with streaming support.

Refactored to match the reference implementation pattern:
- Direct LLM instantiation per node (no class-based agents for LLM calls)
- Streaming support for code generation
- Simplified response handling
"""
import json
import re
from datetime import datetime
from typing import Any, Dict, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import END, StateGraph

from app.config import settings
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager
from app.workflows.state import (
    WorkflowState,
    get_next_executable_step,
    mark_step_completed,
    mark_step_failed,
)

logger = get_logger(__name__)


# =============================================================================
# NOTE: Prompts are defined in individual agent classes under app/agents/
# - PlannerAgent: app/agents/planner.py
# - FlutterEngineerAgent: app/agents/platform/flutter_engineer.py
# - CodeReviewerAgent: app/agents/code_reviewer.py
# - etc.
# 
# This graph file only orchestrates the workflow between agents.
# All agent logic, prompts, and tools are in their respective classes.
# =============================================================================


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_llm() -> ChatGoogleGenerativeAI:
    """Create a fresh LLM instance for each node invocation."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=1.0,
    )


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """Extract JSON from LLM response content.
    
    Handles:
    - JSON wrapped in ```json ... ``` code blocks
    - Raw JSON in the response
    - Malformed responses (returns empty dict)
    """
    if not content:
        return {}
    
    # Try to strip code block wrappers
    code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(code_block_pattern, content, re.DOTALL)
    if match:
        content = match.group(1).strip()
    
    # Find JSON object
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
    
    return {}


async def broadcast_status(project_id: int, agent: str, status: str, message: str) -> None:
    """Send agent status update via WebSocket."""
    await connection_manager.send_agent_status(
        project_id=project_id,
        agent=agent,
        status=status,
        message=message,
    )


# =============================================================================
# AGENT HELPERS
# =============================================================================

def get_primary_agent_for_framework(framework: str) -> str:
    """Get the code engineering agent for a given framework."""
    framework_to_agent = {
        "flutter": "flutter_engineer",
        "react": "react_engineer",
        "nextjs": "nextjs_engineer",
        "next": "nextjs_engineer",
        "next.js": "nextjs_engineer",
        "react_native": "react_native_engineer",
        "reactnative": "react_native_engineer",
    }
    if framework:
        return framework_to_agent.get(framework.lower().strip(), "flutter_engineer")
    return "flutter_engineer"


# =============================================================================
# AGENT NODES (Reference implementation pattern)
# =============================================================================

async def conductor_node(state: WorkflowState) -> WorkflowState:
    """Conductor agent node - master orchestrator entry point.
    
    The Conductor classifies intent, selects appropriate agents, and creates
    an execution plan. This is the new entry point for the workflow.
    """
    from app.agents.base import AgentContext
    from app.agents.conductor import ConductorAgent
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "conductor", "started", "Analyzing your request...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    conductor = ConductorAgent(context)
    
    try:
        # Conductor analyzes and creates plan
        result = await conductor.run({
            "message": state["user_message"],
            "context": {
                "framework": state.get("detected_framework", "flutter"),
            }
        })
        
        intent = result.get("intent", "explicit")
        
        # Broadcast the plan
        await broadcast_status(
            project_id, "conductor", "in_progress",
            f"Intent: {intent} - Creating execution plan..."
        )
        
        # Now delegate to strategist for detailed task decomposition
        # (Conductor provides high-level orchestration, strategist creates atomic steps)
        await broadcast_status(project_id, "conductor", "completed", "Orchestration complete, creating execution plan...")
        
        return {
            **state,
            "conductor_intent": intent,
            "conductor_plan": result.get("plan", ""),
            "current_agent": "conductor",
            "next_agent": "strategist",  # Use Strategist for task decomposition, not legacy planner
        }
        
    except Exception as e:
        logger.error(f"Conductor failed: {e}")
        await broadcast_status(project_id, "conductor", "failed", str(e))
        # Fall back to strategist directly
        return {
            **state,
            "current_agent": "conductor",
            "next_agent": "strategist",
        }


async def sage_node(state: WorkflowState) -> WorkflowState:
    """Sage agent node - strategic advisor for complex decisions.
    
    Called when architecture decisions or debugging after 2+ attempts is needed.
    """
    from app.agents.base import AgentContext
    from app.agents.sage import SageAgent
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "sage", "started", "Sage analyzing problem...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    sage = SageAgent(context)
    
    step = get_next_executable_step(state)
    if not step:
        return state
    
    try:
        result = await sage.run({
            "question": step.get("description", state["user_message"]),
            "context": state.get("conductor_plan", ""),
        })
        
        await broadcast_status(project_id, "sage", "completed", "Strategic analysis complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["sage_analysis"] = result.get("analysis", "")
        new_state["current_agent"] = "sage"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Sage failed: {e}")
        await broadcast_status(project_id, "sage", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def scout_node(state: WorkflowState) -> WorkflowState:
    """Scout agent node - fast codebase exploration.
    
    Used for search, pattern matching, and file discovery.
    """
    from app.agents.base import AgentContext
    from app.agents.scout import ScoutAgent
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "scout", "started", "Scout exploring codebase...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    scout = ScoutAgent(context)
    
    step = get_next_executable_step(state)
    if not step:
        return state
    
    try:
        result = await scout.run({
            "query": step.get("description", state["user_message"]),
        })
        
        await broadcast_status(project_id, "scout", "completed", "Exploration complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["scout_findings"] = result.get("results", [])
        new_state["current_agent"] = "scout"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Scout failed: {e}")
        await broadcast_status(project_id, "scout", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def scholar_node(state: WorkflowState) -> WorkflowState:
    """Scholar agent node - external documentation research.
    
    Searches official docs, OSS repos for examples and best practices.
    """
    from app.agents.base import AgentContext
    from app.agents.scholar import ScholarAgent
    
    project_id = state["project_id"]
    step = get_next_executable_step(state)
    if not step or step["agent"] != "scholar":
        return state
    
    await broadcast_status(project_id, "scholar", "started", "Scholar researching...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = ScholarAgent(context)
        result = await agent.run({
            "query": step.get("description", state["user_message"]),
        })
        
        await broadcast_status(project_id, "scholar", "completed", "Research complete")
        new_state = mark_step_completed(state, step["id"], result)
        new_state["current_agent"] = "scholar"
        return new_state
        
    except Exception as e:
        logger.error(f"Scholar failed: {e}")
        await broadcast_status(project_id, "scholar", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def scribe_node(state: WorkflowState) -> WorkflowState:
    """Scribe agent node - technical documentation writer.
    
    Creates README, API docs, technical guides.
    """
    from app.agents.base import AgentContext
    from app.agents.scribe import ScribeAgent
    
    project_id = state["project_id"]
    step = get_next_executable_step(state)
    if not step or step["agent"] != "scribe":
        return state
    
    await broadcast_status(project_id, "scribe", "started", "Scribe writing docs...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = ScribeAgent(context)
        result = await agent.run({
            "task": step.get("description", state["user_message"]),
        })
        
        await broadcast_status(project_id, "scribe", "completed", "Documentation complete")
        new_state = mark_step_completed(state, step["id"], result)
        new_state["current_agent"] = "scribe"
        return new_state
        
    except Exception as e:
        logger.error(f"Scribe failed: {e}")
        await broadcast_status(project_id, "scribe", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def strategist_node(state: WorkflowState) -> WorkflowState:
    """Strategist agent node - work planner.
    
    Creates detailed execution plans for complex tasks.
    """
    from app.agents.base import AgentContext
    from app.agents.strategist import StrategistAgent
    
    project_id = state["project_id"]
    step = get_next_executable_step(state)
    if not step or step["agent"] != "strategist":
        return state
    
    await broadcast_status(project_id, "strategist", "started", "Strategist planning...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = StrategistAgent(context)
        result = await agent.run({
            "goal": step.get("description", state["user_message"]),
            "context": state.get("conductor_plan", ""),
        })
        
        await broadcast_status(project_id, "strategist", "completed", "Strategic plan ready")
        new_state = mark_step_completed(state, step["id"], result)
        new_state["current_agent"] = "strategist"
        return new_state
        
    except Exception as e:
        logger.error(f"Strategist failed: {e}")
        await broadcast_status(project_id, "strategist", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def vision_node(state: WorkflowState) -> WorkflowState:
    """Vision agent node - multimodal analysis.
    
    Analyzes images, screenshots, PDFs, diagrams.
    """
    from app.agents.base import AgentContext
    from app.agents.vision import VisionAgent
    
    project_id = state["project_id"]
    step = get_next_executable_step(state)
    if not step or step["agent"] != "vision":
        return state
    
    await broadcast_status(project_id, "vision", "started", "Vision analyzing content...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = VisionAgent(context)
        result = await agent.run({
            "question": step.get("description", state["user_message"]),
        })
        
        await broadcast_status(project_id, "vision", "completed", "Visual analysis complete")
        new_state = mark_step_completed(state, step["id"], result)
        new_state["current_agent"] = "vision"
        return new_state
        
    except Exception as e:
        logger.error(f"Vision failed: {e}")
        await broadcast_status(project_id, "vision", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def analyst_node(state: WorkflowState) -> WorkflowState:
    """Analyst agent node - pre-planning analysis.
    
    Identifies hidden requirements and potential failure points.
    """
    from app.agents.base import AgentContext
    from app.agents.analyst import AnalystAgent
    
    project_id = state["project_id"]
    step = get_next_executable_step(state)
    if not step or step["agent"] != "analyst":
        return state
    
    await broadcast_status(project_id, "analyst", "started", "Analyst pre-analyzing...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = AnalystAgent(context)
        result = await agent.run({
            "request": step.get("description", state["user_message"]),
            "context": state.get("conductor_plan", ""),
        })
        
        await broadcast_status(project_id, "analyst", "completed", "Pre-analysis complete")
        new_state = mark_step_completed(state, step["id"], result)
        new_state["analyst_findings"] = result.get("analysis", "")
        new_state["current_agent"] = "analyst"
        return new_state
        
    except Exception as e:
        logger.error(f"Analyst failed: {e}")
        await broadcast_status(project_id, "analyst", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def artisan_node(state: WorkflowState) -> WorkflowState:
    """Artisan agent node - UI/UX specialist.
    
    Creates beautiful, polished user interfaces.
    """
    from app.agents.base import AgentContext
    from app.agents.artisan import ArtisanAgent
    
    project_id = state["project_id"]
    step = get_next_executable_step(state)
    if not step or step["agent"] != "artisan":
        return state
    
    await broadcast_status(project_id, "artisan", "started", "Artisan crafting UI...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = ArtisanAgent(context)
        result = await agent.run({
            "task": step.get("description", state["user_message"]),
        })
        
        # Extract code changes if any
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "artisan", "completed", "UI crafted")
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "artisan"
        return new_state
        
    except Exception as e:
        logger.error(f"Artisan failed: {e}")
        await broadcast_status(project_id, "artisan", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def planner_node(state: WorkflowState) -> WorkflowState:
    """Planner agent node - creates execution plan using PlannerAgent.
    
    Delegates to PlannerAgent.run() which has the complete prompt and logic.
    """
    from app.agents.base import AgentContext
    from app.agents.planner import PlannerAgent
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "planner", "started", "Analyzing request...")
    
    # Determine primary agent based on project framework
    framework = state.get("detected_framework") or "flutter"
    primary_agent = get_primary_agent_for_framework(framework)
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        planner = PlannerAgent(context)
        result = await planner.run({
            "user_message": state["user_message"],
        })
        
        # Extract plan from result
        plan = result.get("plan")
        
        # Convert plan steps to our format
        plan_steps = []
        if plan and hasattr(plan, 'steps'):
            for step in plan.steps:
                # Ensure correct agent is used based on framework
                agent = step.agent
                if agent == "flutter_engineer" and framework != "flutter":
                    agent = primary_agent
                    
                plan_steps.append({
                    "id": step.id,
                    "description": step.description,
                    "agent": agent,
                    "action": step.action,
                    "status": "pending",
                    "result": None,
                    "dependencies": step.dependencies,
                    "file_path": step.file_path,
                })
        
        # Fallback default plan using correct framework agent
        if not plan_steps:
            plan_steps = [
                {"id": 1, "description": state["user_message"], "agent": primary_agent, "action": "implement", "status": "pending", "result": None, "dependencies": [], "file_path": None},
                {"id": 2, "description": "Review code changes", "agent": "code_reviewer", "action": "review", "status": "pending", "result": None, "dependencies": [], "file_path": None},
                {"id": 3, "description": "Commit changes", "agent": "git_operator", "action": "commit", "status": "pending", "result": None, "dependencies": [], "file_path": None},
            ]
        
        # Ensure code_reviewer and git_operator steps
        has_reviewer = any(s["agent"] == "code_reviewer" for s in plan_steps)
        has_git = any(s["agent"] == "git_operator" for s in plan_steps)
        
        if not has_reviewer:
            plan_steps.append({"id": len(plan_steps) + 1, "description": "Review code changes", "agent": "code_reviewer", "action": "review", "status": "pending", "result": None, "dependencies": [], "file_path": None})
        if not has_git:
            plan_steps.append({"id": len(plan_steps) + 1, "description": "Commit changes", "agent": "git_operator", "action": "commit", "status": "pending", "result": None, "dependencies": [], "file_path": None})
        
        await broadcast_status(project_id, "planner", "completed", f"Plan created with {len(plan_steps)} steps")
        
        return {
            **state,
            "plan": {
                "user_request": state["user_message"],
                "summary": plan.summary if plan else "Process user request",
                "steps": plan_steps,
                "estimated_time_seconds": plan.estimated_time_seconds if plan else 120,
            },
            "plan_steps": plan_steps,
            "current_agent": "planner",
            "next_agent": plan_steps[0]["agent"] if plan_steps else primary_agent,
        }
        
    except Exception as e:
        logger.error(f"Planner failed: {e}")
        await broadcast_status(project_id, "planner", "failed", str(e))
        return {
            **state,
            "has_error": True,
            "error_message": str(e),
            "is_complete": True,
        }


async def flutter_engineer_node(state: WorkflowState) -> WorkflowState:
    """Flutter Engineer agent node - delegates to FlutterEngineerAgent.
    
    The FlutterEngineerAgent has complete logic for:
    - Reading existing files from GitHub
    - Surgical edits vs full rewrites
    - Code validation and anti-hallucination
    """
    from app.agents.base import AgentContext
    from app.agents.platform.flutter_engineer import FlutterEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "flutter_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "flutter_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = FlutterEngineerAgent(context)
        result = await agent.run({
            "step": step,
            "user_message": state["user_message"],
            "code_changes": state.get("code_changes", {}),
        })
        
        # Extract code changes from result
        code_changes = state.get("code_changes", {}).copy()
        if result.get("changes"):
            for change in result["changes"]:
                if change.get("path") and change.get("content"):
                    code_changes[change["path"]] = change["content"]
                    await connection_manager.send_file_operation(
                        project_id=project_id,
                        agent="flutter_engineer",
                        operation=change.get("action", "modify"),
                        file_path=change["path"],
                        message=change.get("description", task_description),
                    )
        
        await broadcast_status(project_id, "flutter_engineer", "completed", f"Completed: {task_description[:50]}")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "flutter_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Flutter engineer failed: {e}")
        await broadcast_status(project_id, "flutter_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def code_reviewer_node(state: WorkflowState) -> WorkflowState:
    """Code Reviewer agent node - reviews code changes using CodeReviewerAgent."""
    from app.agents.base import AgentContext
    from app.agents.code_reviewer import CodeReviewerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "code_reviewer":
        # If no explicit review step, check if we have changes to review  
        if not state.get("code_changes"):
            return state
        step = {"id": -1, "agent": "code_reviewer"}
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "code_reviewer", "started", "Reviewing code changes...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    try:
        agent = CodeReviewerAgent(context)
        
        # Format changes for review
        changes = []
        for path, content in state.get("code_changes", {}).items():
            changes.append({
                "file_path": path,
                "content": content,
                "action": "modify",
            })
        
        result = await agent.run({"changes": changes})
        
        review_result = {
            "approved": result.get("approved", True),
            "issues": result.get("issues", []),
            "suggestions": result.get("suggestions", []),
            "severity": result.get("severity", "none"),
        }
        
        status = "approved" if review_result["approved"] else "needs_revision"
        await broadcast_status(project_id, "code_reviewer", "completed", f"Review {status}")
        
        new_state = dict(state)
        new_state["review_result"] = review_result
        new_state["current_agent"] = "code_reviewer"
        
        if step["id"] >= 0:
            new_state = mark_step_completed(new_state, step["id"], review_result)
        
        return new_state
        
    except Exception as e:
        logger.error(f"Code reviewer failed: {e}")
        await broadcast_status(project_id, "code_reviewer", "failed", str(e))
        if step["id"] >= 0:
            return mark_step_failed(state, step["id"], str(e))
        return state


async def git_operator_node(state: WorkflowState) -> WorkflowState:
    """Git Operator agent node - commits changes to GitHub.
    
    Uses the GitOperatorAgent class since it needs GitHub API access.
    """
    from app.agents.base import AgentContext
    from app.agents.git_operator import GitOperatorAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "git_operator":
        return state
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "git_operator", "started", "Committing changes...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = GitOperatorAgent(context)
    
    try:
        files = [
            {"path": path, "content": content}
            for path, content in state.get("code_changes", {}).items()
        ]
        
        result = await agent.run({
            "operation": "commit",
            "files": files,
            "message": f"feat: {state['user_message'][:50]}",
        })
        
        await connection_manager.send_git_operation(
            project_id=project_id,
            operation="commit",
            message=f"Committed {len(files)} file(s)",
            commit_sha=result.get("commit_sha"),
            files_changed=len(files),
        )
        
        await broadcast_status(project_id, "git_operator", "completed", "Changes committed")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["git_result"] = result
        new_state["current_agent"] = "git_operator"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Git operator failed: {e}")
        await broadcast_status(project_id, "git_operator", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def build_deploy_node(state: WorkflowState) -> WorkflowState:
    """Build Deploy agent node - handles CI/CD."""
    from app.agents.base import AgentContext
    from app.agents.build_deploy import BuildDeployAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "build_deploy":
        return state
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "build_deploy", "started", "Starting build...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = BuildDeployAgent(context)
    
    try:
        result = await agent.run({"branch": state["current_branch"]})
        
        await broadcast_status(project_id, "build_deploy", "completed", "Build completed")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["build_result"] = result
        new_state["current_agent"] = "build_deploy"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Build deploy failed: {e}")
        await broadcast_status(project_id, "build_deploy", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def react_engineer_node(state: WorkflowState) -> WorkflowState:
    """React Engineer agent node - generates React/TypeScript code."""
    from app.agents.base import AgentContext
    from app.agents.platform.react_engineer import ReactEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "react_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "react_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = ReactEngineerAgent(context)
    
    try:
        result = await agent.run({"step": step})
        
        # Update code changes
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "react_engineer", "completed", "Code generation complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "react_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"React engineer failed: {e}")
        await broadcast_status(project_id, "react_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def nextjs_engineer_node(state: WorkflowState) -> WorkflowState:
    """Next.js Engineer agent node - generates Next.js App Router code."""
    from app.agents.base import AgentContext
    from app.agents.platform.nextjs_engineer import NextjsEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "nextjs_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "nextjs_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = NextjsEngineerAgent(context)
    
    try:
        result = await agent.run({"step": step})
        
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "nextjs_engineer", "completed", "Code generation complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "nextjs_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Next.js engineer failed: {e}")
        await broadcast_status(project_id, "nextjs_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def react_native_engineer_node(state: WorkflowState) -> WorkflowState:
    """React Native Engineer agent node - generates React Native code."""
    from app.agents.base import AgentContext
    from app.agents.platform.react_native_engineer import ReactNativeEngineerAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "react_native_engineer":
        return state
    
    project_id = state["project_id"]
    task_description = step.get("description", state["user_message"])
    
    await broadcast_status(project_id, "react_native_engineer", "started", f"Working on: {task_description[:50]}...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = ReactNativeEngineerAgent(context)
    
    try:
        result = await agent.run({"step": step})
        
        code_changes = state.get("code_changes", {}).copy()
        if result.get("file_path") and result.get("code"):
            code_changes[result["file_path"]] = result["code"]
        
        await broadcast_status(project_id, "react_native_engineer", "completed", "Code generation complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["code_changes"] = code_changes
        new_state["current_agent"] = "react_native_engineer"
        
        return new_state
        
    except Exception as e:
        logger.error(f"React Native engineer failed: {e}")
        await broadcast_status(project_id, "react_native_engineer", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def backend_integration_node(state: WorkflowState) -> WorkflowState:
    """Backend Integration agent node - sets up Supabase/Firebase/Serverpod."""
    from app.agents.base import AgentContext
    from app.agents.platform.backend_integration import BackendIntegrationAgent
    
    step = get_next_executable_step(state)
    if not step or step["agent"] != "backend_integration":
        return state
    
    project_id = state["project_id"]
    
    await broadcast_status(project_id, "backend_integration", "started", "Setting up backend integration...")
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = BackendIntegrationAgent(context)
    
    try:
        # Detect framework and backend from state or step
        framework = state.get("detected_framework", "flutter")
        backend_type = step.get("backend_type", "supabase")
        
        result = await agent.run({
            "step": step,
            "framework": framework,
            "backend_type": backend_type,
        })
        
        await broadcast_status(project_id, "backend_integration", "completed", f"Backend integration complete")
        
        new_state = mark_step_completed(state, step["id"], result)
        new_state["current_agent"] = "backend_integration"
        
        return new_state
        
    except Exception as e:
        logger.error(f"Backend integration failed: {e}")
        await broadcast_status(project_id, "backend_integration", "failed", str(e))
        return mark_step_failed(state, step["id"], str(e))


async def memory_node(state: WorkflowState) -> WorkflowState:
    """Memory agent node - logs operations to database."""
    from app.agents.base import AgentContext
    from app.agents.memory import MemoryAgent
    
    project_id = state["project_id"]
    
    context = AgentContext(
        project_id=state["project_id"],
        user_id=state["user_id"],
        project_folder=state.get("project_folder"),
        current_branch=state["current_branch"],
        task_id=state["task_id"],
    )
    
    agent = MemoryAgent(context)
    
    try:
        started_at = datetime.fromisoformat(state["started_at"])
        duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        
        # Use lowercase enum values to match PostgreSQL
        operation_type = "agent_task_completed" if not state.get("has_error") else "agent_task_failed"
        
        await agent.run({
            "operation_type": operation_type,
            "agent_type": "system",
            "message": f"Task completed: {state['user_message'][:100]}",
            "status": "completed" if not state.get("has_error") else "failed",
            "duration_ms": duration_ms,
            "details": {
                "steps_completed": len([s for s in state.get("plan_steps", []) if s.get("status") == "completed"]),
                "files_changed": len(state.get("code_changes", {})),
            },
        })
        
    except Exception as e:
        logger.error(f"Memory logging failed: {e}")
    
    return {
        **state,
        "current_agent": "memory",
        "is_complete": True,
        "completed_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# ROUTING
# =============================================================================

def route_next_agent(state: WorkflowState) -> Literal[
    "sage", "scout", "scholar", "scribe", "strategist", "vision", "analyst", "artisan",
    "flutter_engineer", "react_engineer", "nextjs_engineer", "react_native_engineer", "backend_integration",
    "code_reviewer", "git_operator", "build_deploy", "memory", "__end__"
]:
    """Determine the next agent to run based on state."""
    if state.get("has_error"):
        return "memory"
    
    if state.get("is_complete"):
        return END
    
    next_step = get_next_executable_step(state)
    
    if next_step:
        agent = next_step["agent"]
        # Map agent names to valid node names (all 18 agents)
        valid_agents = [
            # Specialized (8)
            "sage", "scout", "scholar", "scribe", 
            "strategist", "vision", "analyst", "artisan",
            # Platform (5)
            "flutter_engineer", "react_engineer", "nextjs_engineer", 
            "react_native_engineer", "backend_integration",
            # Operations (4)
            "code_reviewer", "git_operator", "build_deploy", "memory"
        ]
        if agent in valid_agents:
            return agent
        # Default based on detected framework or fall back to flutter
        framework = state.get("detected_framework", "flutter")
        return get_primary_agent_for_framework(framework)
    
    return "memory"


def create_workflow_graph() -> StateGraph:
    """Create the LangGraph workflow graph with multi-agent orchestration.
    
    Flow: Conductor -> Planner -> Engineers/Specialized Agents -> Review -> Git -> Memory
    """
    graph = StateGraph(WorkflowState)
    
    # Orchestration nodes (NEW)
    graph.add_node("conductor", conductor_node)
    graph.add_node("sage", sage_node)
    graph.add_node("scout", scout_node)
    graph.add_node("scholar", scholar_node)
    graph.add_node("scribe", scribe_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("vision", vision_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("artisan", artisan_node)
    
    # Planning node
    graph.add_node("planner", planner_node)
    
    # Platform engineer nodes
    graph.add_node("flutter_engineer", flutter_engineer_node)
    graph.add_node("react_engineer", react_engineer_node)
    graph.add_node("nextjs_engineer", nextjs_engineer_node)
    graph.add_node("react_native_engineer", react_native_engineer_node)
    graph.add_node("backend_integration", backend_integration_node)
    
    # Operations nodes
    graph.add_node("code_reviewer", code_reviewer_node)
    graph.add_node("git_operator", git_operator_node)
    graph.add_node("build_deploy", build_deploy_node)
    graph.add_node("memory", memory_node)
    
    # Set Conductor as entry point (master orchestrator)
    graph.set_entry_point("conductor")
    
    # Conductor always goes to planner
    graph.add_edge("conductor", "planner")
    
    # Edge mapping for all agents (all 19 agents)
    edge_mapping = {
        # Specialized agents (8)
        "sage": "sage",
        "scout": "scout",
        "scholar": "scholar",
        "scribe": "scribe",
        "strategist": "strategist",
        "vision": "vision",
        "analyst": "analyst",
        "artisan": "artisan",
        # Platform engineers (5)
        "flutter_engineer": "flutter_engineer",
        "react_engineer": "react_engineer",
        "nextjs_engineer": "nextjs_engineer",
        "react_native_engineer": "react_native_engineer",
        "backend_integration": "backend_integration",
        # Operations (4)
        "code_reviewer": "code_reviewer",
        "git_operator": "git_operator",
        "build_deploy": "build_deploy",
        "memory": "memory",
        END: END,
    }
    
    # Planner routes to appropriate agents
    graph.add_conditional_edges("planner", route_next_agent, edge_mapping)
    
    # All specialized agents can route
    specialized_agents = [
        "sage", "scout", "scholar", "scribe", 
        "strategist", "vision", "analyst", "artisan"
    ]
    for agent in specialized_agents:
        graph.add_conditional_edges(agent, route_next_agent, edge_mapping)
    
    # All platform engineers can route to any other agent
    platform_agents = [
        "flutter_engineer", "react_engineer", "nextjs_engineer", 
        "react_native_engineer", "backend_integration",
    ]
    for agent in platform_agents:
        graph.add_conditional_edges(agent, route_next_agent, edge_mapping)
    
    # Operations agents can route
    ops_agents = ["code_reviewer", "git_operator", "build_deploy"]
    for agent in ops_agents:
        graph.add_conditional_edges(agent, route_next_agent, edge_mapping)
    
    graph.add_edge("memory", END)
    
    return graph
