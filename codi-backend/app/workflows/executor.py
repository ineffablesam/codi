"""Workflow executor for running the agent graph."""
from datetime import datetime
from typing import Any, Dict, Optional

from app.agents.base import AgentContext
from app.database import get_db_context
from app.models.project import Project
from app.models.agent_task import AgentTask
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager
from app.workflows.graph import create_workflow_graph
from app.workflows.state import WorkflowState, create_initial_state

logger = get_logger(__name__)


class WorkflowExecutor:
    """Executor for running the agent workflow graph."""

    def __init__(
        self,
        project_id: int,
        user_id: int,
        github_token: str,
        task_id: str,
    ) -> None:
        """Initialize the workflow executor.

        Args:
            project_id: Project ID
            user_id: User ID
            github_token: Decrypted GitHub access token
            task_id: Unique task identifier
        """
        self.project_id = project_id
        self.user_id = user_id
        self.github_token = github_token
        self.task_id = task_id
        self._graph = None
        self._repo_full_name: Optional[str] = None
        self._current_branch: str = "main"

    async def _load_project_info(self) -> None:
        """Load project information from database."""
        async with get_db_context() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Project).where(Project.id == self.project_id)
            )
            project = result.scalar_one_or_none()

            if project:
                self._repo_full_name = project.github_repo_full_name
                self._current_branch = project.github_current_branch or "main"

    def _patch_agent_context(self, state: WorkflowState) -> None:
        """Patch agent context with GitHub token.

        This is a workaround since the state doesn't carry the token
        for security reasons. Each agent node will have access to the
        token through the executor.

        Args:
            state: Current workflow state
        """
        # The agents will be initialized with the token in the graph nodes
        # This method can be used for additional patching if needed
        pass

    @property
    def graph(self):
        """Get or create the workflow graph."""
        if self._graph is None:
            graph_builder = create_workflow_graph()
            self._graph = graph_builder.compile()
        return self._graph

    async def execute(self, user_message: str) -> Dict[str, Any]:
        """Execute the workflow for a user message.

        Args:
            user_message: The user's request message

        Returns:
            Final workflow state as dictionary
        """
        start_time = datetime.utcnow()

        # Load project info
        await self._load_project_info()

        # Create initial state
        initial_state = create_initial_state(
            project_id=self.project_id,
            user_id=self.user_id,
            task_id=self.task_id,
            user_message=user_message,
            repo_full_name=self._repo_full_name,
            current_branch=self._current_branch,
            github_token=self.github_token,
        )

        logger.info(
            f"Starting workflow execution",
            task_id=self.task_id,
            project_id=self.project_id,
            user_message=user_message[:100],
        )

        # Notify start
        await connection_manager.broadcast_to_project(
            self.project_id,
            {
                "type": "agent_status",
                "agent": "system",
                "status": "started",
                "message": "Processing your request...",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        # Update task status in DB
        async with get_db_context() as session:
            from sqlalchemy import update
            await session.execute(
                update(AgentTask)
                .where(AgentTask.id == self.task_id)
                .values(status="processing", started_at=datetime.utcnow())
            )
            await session.commit()

        try:
            # Run the graph
            # Note: In a full implementation, we'd need to inject the github_token
            # into each agent. This is done through AgentContext in the node functions.
            final_state = await self.graph.ainvoke(
                initial_state,
                {"recursion_limit": 50},
            )

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"Workflow completed",
                task_id=self.task_id,
                duration_seconds=duration,
                has_error=final_state.get("has_error", False),
            )

            # Update task status in DB
            async with get_db_context() as session:
                from sqlalchemy import update
                status = "completed" if not final_state.get("has_error") else "failed"
                error_msg = final_state.get("error_message") if final_state.get("has_error") else None
                
                await session.execute(
                    update(AgentTask)
                    .where(AgentTask.id == self.task_id)
                    .values(
                        status=status,
                        completed_at=datetime.utcnow(),
                        error=error_msg,
                        result=dict(final_state) if not final_state.get("has_error") else None
                    )
                )
                await session.commit()

            return dict(final_state)

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            # Update task status in DB on failure
            async with get_db_context() as session:
                from sqlalchemy import update
                await session.execute(
                    update(AgentTask)
                    .where(AgentTask.id == self.task_id)
                    .values(
                        status="failed",
                        completed_at=datetime.utcnow(),
                        error=str(e)
                    )
                )
                await session.commit()

            raise

    async def execute_step(
        self,
        state: WorkflowState,
        agent_name: str,
    ) -> WorkflowState:
        """Execute a single step in the workflow.

        This is useful for manual step-by-step execution.

        Args:
            state: Current workflow state
            agent_name: Name of the agent to run

        Returns:
            Updated workflow state
        """
        from app.workflows.graph import (
            planner_node,
            flutter_engineer_node,
            code_reviewer_node,
            git_operator_node,
            build_deploy_node,
            memory_node,
        )

        agents = {
            "planner": planner_node,
            "flutter_engineer": flutter_engineer_node,
            "code_reviewer": code_reviewer_node,
            "git_operator": git_operator_node,
            "build_deploy": build_deploy_node,
            "memory": memory_node,
        }

        if agent_name not in agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        node_func = agents[agent_name]
        return await node_func(state)


async def run_workflow(
    project_id: int,
    user_id: int,
    github_token: str,
    task_id: str,
    user_message: str,
) -> Dict[str, Any]:
    """Convenience function to run a workflow.

    Args:
        project_id: Project ID
        user_id: User ID
        github_token: Decrypted GitHub access token
        task_id: Unique task identifier
        user_message: The user's request message

    Returns:
        Final workflow state
    """
    executor = WorkflowExecutor(
        project_id=project_id,
        user_id=user_id,
        github_token=github_token,
        task_id=task_id,
    )

    return await executor.execute(user_message)
