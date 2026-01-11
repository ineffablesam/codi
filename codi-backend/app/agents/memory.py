"""Memory agent for history and state persistence."""
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.tools import BaseTool, tool
from sqlalchemy import select

from app.agents.base import AgentContext, BaseAgent
from app.database import get_db_context
from app.models.operation_log import AgentType, OperationLog, OperationType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryAgent(BaseAgent):
    """Agent responsible for maintaining operation history.

    The Memory agent records all agent operations, maintains
    audit trails, and provides context for future operations.
    """

    name = "memory"
    description = "Persistent state and audit trail"

    system_prompt = """You are the Memory Agent for Codi, an AI-powered Flutter development platform.

Your role is to maintain the complete history of all operations.

## Your Responsibilities:
1. Record all agent operations
2. Maintain operation logs
3. Track build history
4. Store deployment records
5. Enable operation replay and debugging"""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Memory agent."""

        @tool
        def get_recent_operations(limit: int = 10) -> str:
            """Get recent operations for the project.

            Args:
                limit: Maximum number of operations to return

            Returns:
                JSON list of recent operations
            """
            import json

            async def fetch_operations() -> str:
                async with get_db_context() as session:
                    result = await session.execute(
                        select(OperationLog)
                        .where(OperationLog.project_id == self.context.project_id)
                        .order_by(OperationLog.created_at.desc())
                        .limit(limit)
                    )
                    logs = result.scalars().all()
                    return json.dumps([log.to_dict() for log in logs], default=str)

            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(fetch_operations())

        return [get_recent_operations]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log an operation to the database.

        Args:
            input_data: Dictionary with operation details

        Returns:
            Dictionary with logging confirmation
        """
        operation_type = input_data.get("operation_type", "agent_task_completed")
        agent_type = input_data.get("agent_type", "system")
        message = input_data.get("message", "Operation completed")
        status = input_data.get("status", "completed")
        details = input_data.get("details", {})
        duration_ms = input_data.get("duration_ms")

        # Emit start status
        await self.emit_status(
            status="started",
            message="Recording operation history",
        )

        try:
            # Create operation log entry
            async with get_db_context() as session:
                log_entry = OperationLog(
                    user_id=self.context.user_id,
                    project_id=self.context.project_id,
                    operation_type=OperationType(operation_type) if operation_type in [e.value for e in OperationType] else OperationType.AGENT_TASK_COMPLETED,
                    agent_type=AgentType(agent_type) if agent_type in [e.value for e in AgentType] else AgentType.SYSTEM,
                    message=message,
                    status=status,
                    details=details,
                    duration_ms=duration_ms,
                )
                session.add(log_entry)
                await session.commit()

                operation_id = f"op_{log_entry.id}"

            # Calculate duration string
            duration_str = None
            if duration_ms:
                seconds = duration_ms / 1000
                if seconds >= 60:
                    duration_str = f"{int(seconds // 60)}m {int(seconds % 60)}s"
                else:
                    duration_str = f"{seconds:.1f}s"

            # Emit completion
            await self.emit_status(
                status="completed",
                message="✅ Operation logged successfully",
                details={
                    "operation_id": operation_id,
                    "duration": duration_str,
                    "success": status == "completed",
                },
            )

            return {
                "operation_id": operation_id,
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Failed to log operation: {e}")
            await self.emit_error(
                error=str(e),
                message="Failed to log operation",
            )
            # Don't raise - memory logging failure shouldn't stop the workflow
            return {
                "logged": False,
                "error": str(e),
            }

    async def log_operation(
        self,
        operation_type: OperationType,
        agent_type: AgentType,
        message: str,
        status: str = "completed",
        details: Dict[str, Any] | None = None,
        file_path: str | None = None,
        commit_sha: str | None = None,
        branch_name: str | None = None,
        lines_added: int | None = None,
        lines_removed: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        """Helper method to log an operation directly.

        Args:
            operation_type: Type of operation
            agent_type: Agent that performed the operation
            message: Human-readable message
            status: Operation status
            details: Additional details
            file_path: File path if applicable
            commit_sha: Git commit SHA if applicable
            branch_name: Git branch name if applicable
            lines_added: Lines added if applicable
            lines_removed: Lines removed if applicable
            duration_ms: Duration in milliseconds
            error_message: Error message if failed
        """
        try:
            async with get_db_context() as session:
                log_entry = OperationLog(
                    user_id=self.context.user_id,
                    project_id=self.context.project_id,
                    operation_type=operation_type,
                    agent_type=agent_type,
                    message=message,
                    status=status,
                    details=details,
                    file_path=file_path,
                    commit_sha=commit_sha,
                    branch_name=branch_name,
                    lines_added=lines_added,
                    lines_removed=lines_removed,
                    duration_ms=duration_ms,
                    error_message=error_message,
                )
                session.add(log_entry)
                await session.commit()

                logger.debug(
                    f"Logged operation",
                    operation_type=operation_type.value,
                    agent_type=agent_type.value,
                )

        except Exception as e:
            logger.error(f"Failed to log operation: {e}")

    async def log_agent_start(
        self,
        agent_name: str,
        task_description: str,
    ) -> None:
        """Quick method for agents to log task start.
        
        Args:
            agent_name: Name of the agent
            task_description: Description of the task being started
        """
        try:
            agent_type = AgentType(agent_name)
        except ValueError:
            agent_type = AgentType.SYSTEM
            
        await self.log_operation(
            operation_type=OperationType.AGENT_TASK_STARTED,
            agent_type=agent_type,
            message=f"Started: {task_description[:100]}",
            status="started",
        )

    async def log_agent_complete(
        self,
        agent_name: str,
        result_summary: str,
        duration_ms: int | None = None,
        details: Dict[str, Any] | None = None,
    ) -> None:
        """Quick method for agents to log task completion.
        
        Args:
            agent_name: Name of the agent
            result_summary: Summary of the result
            duration_ms: Duration in milliseconds
            details: Additional details
        """
        try:
            agent_type = AgentType(agent_name)
        except ValueError:
            agent_type = AgentType.SYSTEM
            
        await self.log_operation(
            operation_type=OperationType.AGENT_TASK_COMPLETED,
            agent_type=agent_type,
            message=f"Completed: {result_summary[:100]}",
            status="completed",
            duration_ms=duration_ms,
            details=details,
        )

    async def log_agent_error(
        self,
        agent_name: str,
        error_message: str,
        duration_ms: int | None = None,
    ) -> None:
        """Quick method for agents to log task failures.
        
        Args:
            agent_name: Name of the agent
            error_message: Error description
            duration_ms: Duration in milliseconds
        """
        try:
            agent_type = AgentType(agent_name)
        except ValueError:
            agent_type = AgentType.SYSTEM
            
        await self.log_operation(
            operation_type=OperationType.AGENT_TASK_COMPLETED,
            agent_type=agent_type,
            message=f"Failed: {error_message[:100]}",
            status="failed",
            duration_ms=duration_ms,
            error_message=error_message,
        )

    async def get_project_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent operations as context for agents.
        
        Provides historical context to help agents understand
        what has been done previously in the project.
        
        Args:
            limit: Maximum number of operations to return
            
        Returns:
            List of recent operation dictionaries
        """
        import json
        
        try:
            async with get_db_context() as session:
                result = await session.execute(
                    select(OperationLog)
                    .where(OperationLog.project_id == self.context.project_id)
                    .order_by(OperationLog.created_at.desc())
                    .limit(limit)
                )
                logs = result.scalars().all()
                return [log.to_dict() for log in logs]
        except Exception as e:
            logger.error(f"Failed to get project context: {e}")
            return []

