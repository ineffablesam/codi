"""LangGraph state definition for agent orchestration."""
from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with right taking precedence."""
    result = left.copy()
    result.update(right)
    return result


def append_list(left: List[Any], right: List[Any]) -> List[Any]:
    """Append two lists."""
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right


class PlanStep(TypedDict):
    """A single step in the execution plan."""

    id: int
    description: str
    agent: str
    dependencies: List[int]
    file_path: Optional[str]
    action: str
    status: str  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]]


class WorkflowState(TypedDict):
    """State maintained throughout the agent workflow.

    This state is passed between agents and updated as work progresses.
    """

    # Context
    project_id: int
    user_id: int
    task_id: str
    repo_full_name: Optional[str]
    current_branch: str
    github_token: Optional[str]

    # User input
    user_message: str

    # Messages for LLM context
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Execution plan from Planner
    plan: Optional[Dict[str, Any]]
    plan_steps: List[PlanStep]
    current_step_index: int

    # Current agent
    current_agent: str
    next_agent: Optional[str]

    # Results from agents
    code_changes: Annotated[Dict[str, str], merge_dicts]  # file_path -> content
    review_result: Optional[Dict[str, Any]]
    git_result: Optional[Dict[str, Any]]
    build_result: Optional[Dict[str, Any]]

    # Workflow control
    is_complete: bool
    has_error: bool
    error_message: Optional[str]

    # Timing
    started_at: str
    completed_at: Optional[str]


def create_initial_state(
    project_id: int,
    user_id: int,
    task_id: str,
    user_message: str,
    repo_full_name: Optional[str] = None,
    current_branch: str = "main",
    github_token: Optional[str] = None,
) -> WorkflowState:
    """Create the initial workflow state.

    Args:
        project_id: Project ID
        user_id: User ID
        task_id: Unique task identifier
        user_message: User's request message
        repo_full_name: GitHub repository full name
        current_branch: Current git branch
        github_token: GitHub access token for API operations

    Returns:
        Initial WorkflowState
    """
    return WorkflowState(
        project_id=project_id,
        user_id=user_id,
        task_id=task_id,
        repo_full_name=repo_full_name,
        current_branch=current_branch,
        github_token=github_token,
        user_message=user_message,
        messages=[],
        plan=None,
        plan_steps=[],
        current_step_index=0,
        current_agent="planner",
        next_agent=None,
        code_changes={},
        review_result=None,
        git_result=None,
        build_result=None,
        is_complete=False,
        has_error=False,
        error_message=None,
        started_at=datetime.utcnow().isoformat(),
        completed_at=None,
    )


def get_pending_steps(state: WorkflowState) -> List[PlanStep]:
    """Get steps that are pending execution.

    Args:
        state: Current workflow state

    Returns:
        List of pending steps
    """
    return [step for step in state["plan_steps"] if step["status"] == "pending"]


def get_completed_steps(state: WorkflowState) -> List[PlanStep]:
    """Get steps that have been completed.

    Args:
        state: Current workflow state

    Returns:
        List of completed steps
    """
    return [step for step in state["plan_steps"] if step["status"] == "completed"]


def can_execute_step(step: PlanStep, state: WorkflowState) -> bool:
    """Check if a step can be executed (all dependencies met).

    Args:
        step: Step to check
        state: Current workflow state

    Returns:
        True if step can be executed
    """
    if step["status"] != "pending":
        return False

    completed_ids = {s["id"] for s in get_completed_steps(state)}

    for dep_id in step["dependencies"]:
        if dep_id not in completed_ids:
            return False

    return True


def get_next_executable_step(state: WorkflowState) -> Optional[PlanStep]:
    """Get the next step that can be executed.

    Args:
        state: Current workflow state

    Returns:
        Next executable step or None
    """
    for step in state["plan_steps"]:
        if can_execute_step(step, state):
            return step
    return None


def mark_step_completed(
    state: WorkflowState,
    step_id: int,
    result: Dict[str, Any] | None = None,
) -> WorkflowState:
    """Mark a step as completed.

    Args:
        state: Current workflow state
        step_id: ID of the step to mark
        result: Optional result data

    Returns:
        Updated state
    """
    new_steps = []
    for step in state["plan_steps"]:
        if step["id"] == step_id:
            new_step = step.copy()
            new_step["status"] = "completed"
            new_step["result"] = result
            new_steps.append(new_step)
        else:
            new_steps.append(step)

    new_state = dict(state)
    new_state["plan_steps"] = new_steps
    return WorkflowState(**new_state)


def mark_step_failed(
    state: WorkflowState,
    step_id: int,
    error: str,
) -> WorkflowState:
    """Mark a step as failed.

    Args:
        state: Current workflow state
        step_id: ID of the step to mark
        error: Error message

    Returns:
        Updated state
    """
    new_steps = []
    for step in state["plan_steps"]:
        if step["id"] == step_id:
            new_step = step.copy()
            new_step["status"] = "failed"
            new_step["result"] = {"error": error}
            new_steps.append(new_step)
        else:
            new_steps.append(step)

    new_state = dict(state)
    new_state["plan_steps"] = new_steps
    new_state["has_error"] = True
    new_state["error_message"] = error
    return WorkflowState(**new_state)
