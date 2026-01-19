"""WebSocket message handlers."""
from datetime import datetime
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


# Track active browser agents by project_id for interaction routing
_active_browser_agents: Dict[int, Any] = {}


class WebSocketHandler:
    """Handler for WebSocket messages from clients."""

    def __init__(self, websocket: WebSocket, project_id: int, user_id: int) -> None:
        """Initialize WebSocket handler.

        Args:
            websocket: WebSocket connection
            project_id: Project ID
            user_id: User ID
        """
        self.websocket = websocket
        self.project_id = project_id
        self.user_id = user_id

    async def handle_message(self, data: Dict[str, Any]) -> None:
        """Handle an incoming WebSocket message.

        Args:
            data: Parsed JSON message data
        """
        message_type = data.get("type", "")

        if message_type == "ping":
            await self._handle_ping()
        elif message_type == "user_message":
            await self._handle_user_message(data)
        elif message_type == "user_input_response":
            await self._handle_user_input_response(data)
        elif message_type == "user_interaction":
            await self._handle_user_interaction(data)
        elif message_type == "plan_approval":
            await self._handle_plan_approval(data)
        else:
            logger.warning(f"Unknown WebSocket message type: {message_type}")

    async def _handle_ping(self) -> None:
        """Handle ping message with pong response."""
        await connection_manager.send_personal_message(
            self.websocket,
            {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _handle_user_message(self, data: Dict[str, Any]) -> None:
        """Handle user message to trigger agent workflow.

        Args:
            data: Message data containing the user's message
        """
        message = data.get("message", "").strip()
        browser_mode = data.get("browser_mode", False)

        if not message:
            await connection_manager.send_personal_message(
                self.websocket,
                {
                    "type": "error",
                    "message": "Empty message received",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            return

        logger.info(
            f"Received user message via WebSocket",
            project_id=self.project_id,
            user_id=self.user_id,
            message_length=len(message),
            browser_mode=browser_mode,
        )

        if browser_mode:
            # Route to browser agent for AI-driven browser automation
            await self._handle_browser_agent_message(message, data)
        else:
            # Route to coding agent (existing behavior)
            await self._handle_coding_agent_message(message)

    async def _handle_browser_agent_message(self, message: str, data: Dict[str, Any]) -> None:
        """Handle message routed to browser agent.
        
        Args:
            message: User's request message
            data: Full message data including optional initial_url
        """
        from app.agent.browser_agent import BrowserAgent
        
        initial_url = data.get("initial_url", "https://google.com")
        
        try:
            # Create and track agent instance for interactions
            agent = BrowserAgent(project_id=self.project_id, user_id=self.user_id)
            _active_browser_agents[self.project_id] = agent
            
            try:
                # Run browser agent (handles its own WebSocket broadcasting)
                await agent.run(user_message=message, initial_url=initial_url)
            finally:
                # Cleanup tracking and resources
                _active_browser_agents.pop(self.project_id, None)
                await agent.close()
                
        except Exception as e:
            logger.error(f"Browser agent failed: {e}")
            await connection_manager.send_error(
                self.project_id,
                "browser",
                str(e),
                "Browser agent failed",
            )

    async def _handle_user_interaction(self, data: Dict[str, Any]) -> None:
        """Handle user interaction event (mouse/keyboard)."""
        agent_type = data.get("agent")
        payload = data.get("payload")
        
        if agent_type == "browser" and self.project_id in _active_browser_agents:
            agent = _active_browser_agents[self.project_id]
            agent.handle_interaction(payload)
        else:
            logger.debug(f"Received user interaction for {agent_type} but no active agent found")

    async def _handle_coding_agent_message(self, message: str) -> None:
        """Handle message routed to coding agent.
        
        Args:
            message: User's request message
        """
        # Import here to avoid circular imports
        from app.api.v1.routes.agents import submit_agent_task_internal

        try:
            # Submit the task
            task_response = await submit_agent_task_internal(
                project_id=self.project_id,
                user_id=self.user_id,
                message=message,
            )

            # Confirm task submission
            await connection_manager.send_personal_message(
                self.websocket,
                {
                    "type": "task_submitted",
                    "task_id": task_response.get("task_id"),
                    "message": "Task submitted successfully",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            await connection_manager.send_error(
                self.project_id,
                "system",
                str(e),
                "Failed to submit task",
            )

    async def _handle_user_input_response(self, data: Dict[str, Any]) -> None:
        """Handle user response to an input request.

        Args:
            data: Response data from the user
        """
        response = data.get("response", "")

        logger.info(
            f"Received user input response",
            project_id=self.project_id,
            user_id=self.user_id,
        )

        # Store the response or forward to the agent
        # This would typically be handled through a callback mechanism
        # For now, we'll broadcast it so the agent can pick it up
        await connection_manager.broadcast_to_project(
            self.project_id,
            {
                "type": "user_input_received",
                "response": response,
                "user_id": self.user_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def _handle_plan_approval(self, data: Dict[str, Any]) -> None:
        """Handle plan approval or rejection from the user.
        
        Args:
            data: Approval data containing plan_id and approved flag
        """
        plan_id = data.get("plan_id")
        approved = data.get("approved", False)
        comment = data.get("comment", "")
        
        logger.info(
            f"Received plan {'approval' if approved else 'rejection'}",
            project_id=self.project_id,
            plan_id=plan_id,
            approved=approved,
        )
        
        # Get the active agent for this project and signal approval
        from app.agent.agent import get_active_agent
        agent = get_active_agent(self.project_id)
        
        if agent:
            agent.handle_approval_response(approved)
        else:
            logger.warning(f"No active agent found for project {self.project_id}")
        
        # Also update the plan status in the database via API
        if plan_id:
            try:
                from app.core.database import get_db_context
                from app.models.plan import ImplementationPlan, PlanStatus
                from sqlalchemy import select
                
                async with get_db_context() as session:
                    result = await session.execute(
                        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
                    )
                    plan = result.scalar_one_or_none()
                    
                    if plan:
                        if approved:
                            plan.status = PlanStatus.IN_PROGRESS
                            plan.approved_at = datetime.utcnow()
                        else:
                            plan.status = PlanStatus.REJECTED
                            plan.rejected_at = datetime.utcnow()
                        
                        await session.commit()
                        
                        # Send signal to agent via Redis (instant)
                        try:
                            from app.api.websocket.redis_broadcaster import redis_broadcaster
                            await redis_broadcaster.send_agent_signal(
                                self.project_id,
                                "plan_approval",
                                {
                                    "plan_id": plan_id,
                                    "approved": approved
                                }
                            )
                        except Exception as e:
                            logger.error(f"Failed to send agent signal: {e}")
                        
                        # Broadcast the status change
                        await connection_manager.broadcast_to_project(
                            self.project_id,
                            {
                                "type": "plan_approved" if approved else "plan_rejected",
                                "plan_id": plan_id,
                                "message": comment or ("Plan approved" if approved else "Plan rejected"),
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        )
            except Exception as e:
                logger.error(f"Failed to update plan status: {e}")


async def websocket_endpoint_handler(
    websocket: WebSocket,
    project_id: int,
    user_id: int,
) -> None:
    """Main WebSocket endpoint handler.

    Args:
        websocket: WebSocket connection
        project_id: Project ID from path
        user_id: User ID from authenticated token
    """
    await connection_manager.connect(websocket, project_id)

    handler = WebSocketHandler(websocket, project_id, user_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            await handler.handle_message(data)

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket disconnected",
            project_id=project_id,
            user_id=user_id,
        )
    except Exception as e:
        logger.error(
            f"WebSocket error: {e}",
            project_id=project_id,
            user_id=user_id,
        )
    finally:
        await connection_manager.disconnect(websocket)
