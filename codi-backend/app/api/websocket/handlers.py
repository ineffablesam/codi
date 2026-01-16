"""WebSocket message handlers."""
from datetime import datetime
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


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
        )

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
