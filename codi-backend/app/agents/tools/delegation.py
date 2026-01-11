"""Delegation tools for agent orchestration.

Provides tools for the Conductor to delegate tasks to specialized agents,
manage background tasks, and retrieve results.
"""
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool, BaseTool

from app.agents.base import AgentContext
from app.agents.background_manager import background_manager
from app.agents.types import LaunchInput
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_delegate_task_tool(context: AgentContext) -> BaseTool:
    """Create a tool for delegating tasks to other agents.
    
    Args:
        context: Agent context with project info
        
    Returns:
        LangChain tool for delegation
    """
    
    @tool
    async def delegate_task(
        agent: str,
        task: str,
        expected_outcome: str,
        context_info: str = "",
        run_in_background: bool = False,
        category: Optional[str] = None,
    ) -> str:
        """Delegate a task to a specialized agent.
        
        Args:
            agent: Name of the agent to delegate to (sage, scholar, scout, artisan, etc.)
            task: Clear description of the task
            expected_outcome: What the agent should deliver
            context_info: Additional context for the agent
            run_in_background: Whether to run as a background task
            category: Optional category for specialized handling (visual, logic, mobile)
        
        Returns:
            Result from the agent or task ID for background tasks
        """
        # Build the delegation prompt
        prompt = f"""## DELEGATED TASK

### Task
{task}

### Expected Outcome
{expected_outcome}
"""
        if context_info:
            prompt += f"\n### Context\n{context_info}\n"
        
        logger.info(f"Delegating to {agent}: {task[:50]}...")
        
        if run_in_background:
            # Launch as background task
            try:
                input_data = LaunchInput(
                    description=task[:100],
                    prompt=prompt,
                    agent=agent,
                    parent_session_id=f"project_{context.project_id}",
                    category=category,
                )
                
                bg_task = await background_manager.launch(input_data)
                
                return f"""Task delegated to {agent} as background task.

Task ID: {bg_task.id}
Session ID: {bg_task.session_id}
Status: {bg_task.status.value}

Use `background_output(task_id="{bg_task.id}")` to check results."""
            
            except Exception as e:
                logger.error(f"Background delegation failed: {e}")
                return f"❌ Failed to launch background task: {e}"
        
        else:
            # Synchronous delegation - actually run the agent
            try:
                agent_instance = _get_agent_instance(agent, context)
                
                if agent_instance is None:
                    return f"❌ Unknown agent: {agent}. Available: {', '.join(AGENT_REGISTRY.keys())}"
                
                # Run the agent with the task
                input_data = {
                    "message": task,
                    "task": task,
                    "goal": task,
                    "query": task,
                    "request": task,
                    "context": context_info,
                    "expected_outcome": expected_outcome,
                }
                
                result = await agent_instance.run(input_data)
                
                # Format the result
                if isinstance(result, dict):
                    # Extract key results
                    content = result.get("plan") or result.get("analysis") or result.get("research") or result.get("findings") or result.get("implementation") or result.get("documentation") or str(result)
                    if hasattr(content, "model_dump"):
                        content = str(content.model_dump())
                    return f"""✅ Task completed by {agent}.

{content}"""
                else:
                    return f"""✅ Task completed by {agent}.

{result}"""
                    
            except Exception as e:
                logger.error(f"Synchronous delegation failed: {e}")
                return f"❌ Delegation to {agent} failed: {e}"
    
    return delegate_task


# Agent registry for delegation
AGENT_REGISTRY = {}


def _get_agent_instance(agent_name: str, context: AgentContext):
    """Get an agent instance by name.
    
    Args:
        agent_name: Name of the agent
        context: Agent context
        
    Returns:
        Agent instance or None if not found
    """
    # Lazy import to avoid circular dependencies
    if not AGENT_REGISTRY:
        _populate_agent_registry()
    
    agent_class = AGENT_REGISTRY.get(agent_name)
    if agent_class is None:
        return None
    
    return agent_class(context)


def _populate_agent_registry():
    """Populate the agent registry with available agents."""
    global AGENT_REGISTRY
    
    try:
        from app.agents.conductor import ConductorAgent
        from app.agents.sage import SageAgent
        from app.agents.scholar import ScholarAgent
        from app.agents.scout import ScoutAgent
        from app.agents.artisan import ArtisanAgent
        from app.agents.scribe import ScribeAgent
        from app.agents.vision import VisionAgent
        from app.agents.strategist import StrategistAgent
        from app.agents.analyst import AnalystAgent
        from app.agents.planner import PlannerAgent
        from app.agents.code_reviewer import CodeReviewerAgent
        from app.agents.git_operator import GitOperatorAgent
        from app.agents.build_deploy import BuildDeployAgent
        from app.agents.memory import MemoryAgent
        
        AGENT_REGISTRY.update({
            "conductor": ConductorAgent,
            "sage": SageAgent,
            "scholar": ScholarAgent,
            "scout": ScoutAgent,
            "artisan": ArtisanAgent,
            "scribe": ScribeAgent,
            "vision": VisionAgent,
            "strategist": StrategistAgent,
            "analyst": AnalystAgent,
            "planner": PlannerAgent,
            "code_reviewer": CodeReviewerAgent,
            "git_operator": GitOperatorAgent,
            "build_deploy": BuildDeployAgent,
            "memory": MemoryAgent,
        })
        
        # Try to import platform engineers
        try:
            from app.agents.platform import (
                FlutterEngineerAgent,
                ReactEngineerAgent,
                NextjsEngineerAgent,
                ReactNativeEngineerAgent,
                BackendIntegrationAgent,
            )
            AGENT_REGISTRY.update({
                "flutter_engineer": FlutterEngineerAgent,
                "react_engineer": ReactEngineerAgent,
                "nextjs_engineer": NextjsEngineerAgent,
                "react_native_engineer": ReactNativeEngineerAgent,
                "backend_integration": BackendIntegrationAgent,
            })
        except ImportError:
            logger.warning("Platform engineers not available")
            
    except Exception as e:
        logger.error(f"Failed to populate agent registry: {e}")


def create_background_output_tool() -> BaseTool:
    """Create a tool for retrieving background task output."""
    
    @tool
    def background_output(task_id: str) -> str:
        """Get the output from a background task.
        
        Args:
            task_id: The ID of the background task
            
        Returns:
            Task status and output if available
        """
        task = background_manager.get_task(task_id)
        
        if not task:
            return f"❌ Task not found: {task_id}"
        
        duration = background_manager._format_duration(
            task.started_at, task.completed_at
        )
        
        if task.status.value == "running":
            return f"""⏳ Task still running...

Task ID: {task.id}
Agent: {task.agent}
Duration: {duration}
Progress: {task.progress.tool_calls} tool calls

Last activity: {task.progress.last_tool or 'starting'}"""
        
        elif task.status.value == "completed":
            return f"""✅ Task completed!

Task ID: {task.id}
Agent: {task.agent}
Duration: {duration}

Result:
{task.result or '(No output captured)'}"""
        
        elif task.status.value == "failed":
            return f"""❌ Task failed!

Task ID: {task.id}
Agent: {task.agent}
Duration: {duration}

Error: {task.error}"""
        
        else:
            return f"""Task {task.id} status: {task.status.value}

Agent: {task.agent}
Duration: {duration}"""
    
    return background_output


def create_background_cancel_tool() -> BaseTool:
    """Create a tool for cancelling background tasks."""
    
    @tool
    async def background_cancel(
        task_id: Optional[str] = None,
        all_tasks: bool = False,
    ) -> str:
        """Cancel background tasks.
        
        Args:
            task_id: Specific task ID to cancel
            all_tasks: If True, cancel all running tasks
            
        Returns:
            Cancellation result
        """
        if all_tasks:
            count = await background_manager.cancel_all()
            return f"✅ Cancelled {count} background task(s)"
        
        elif task_id:
            success = await background_manager.cancel(task_id)
            if success:
                return f"✅ Cancelled task {task_id}"
            else:
                return f"❌ Task not found: {task_id}"
        
        else:
            return "❌ Specify either task_id or all_tasks=True"
    
    return background_cancel


def create_background_status_tool() -> BaseTool:
    """Create a tool for checking all background task statuses."""
    
    @tool
    def background_status() -> str:
        """Get status of all background tasks.
        
        Returns:
            Summary of all running and recent tasks
        """
        running = background_manager.get_running_tasks()
        
        if not running:
            return "No background tasks currently running."
        
        lines = [f"📋 {len(running)} background task(s) running:\n"]
        
        for task in running:
            duration = background_manager._format_duration(task.started_at, None)
            lines.append(f"""• **{task.id}** - {task.agent}
  Task: {task.description[:50]}...
  Duration: {duration}
  Progress: {task.progress.tool_calls} tool calls
""")
        
        return "\n".join(lines)
    
    return background_status
