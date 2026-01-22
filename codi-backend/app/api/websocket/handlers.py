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
        
        # Log all messages except high-frequency ones
        if message_type not in ("ping",):
            logger.info(f"WS message received: {message_type}")

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
        elif message_type == "start_interactive_browser":
            await self._handle_start_interactive_browser(data)
        elif message_type == "end_browser_session":
            await self._handle_end_browser_session(data)
        elif message_type == "browser_navigation":
            await self._handle_browser_navigation(data)
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

    async def _handle_start_interactive_browser(self, data: Dict[str, Any]) -> None:
        """Start an interactive browser session (no AI control).
        
        User can directly control the browser via mouse/keyboard.
        The session streams frames but doesn't run the AI ReAct loop.
        """
        import asyncio
        import httpx
        import websockets
        import json
        
        initial_url = data.get("initial_url", "https://google.com")
        
        logger.info(
            f"Starting interactive browser session",
            project_id=self.project_id,
            initial_url=initial_url,
        )
        
        try:
            # Create browser session via browser-agent service
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://browser-agent:3001/session",
                    json={"initial_url": initial_url}
                )
                response.raise_for_status()
                session_data = response.json()
                session_id = session_data["session_id"]
            
            # Store session in Redis for interaction forwarding
            from app.api.websocket.redis_broadcaster import redis_broadcaster
            await redis_broadcaster.connect()
            session_key = f"browser_session:{self.project_id}"
            await redis_broadcaster._redis.set(session_key, session_id, ex=3600)
            
            logger.info(f"Interactive browser session created: {session_id}")
            
            # Notify frontend that session is ready
            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "agent_status",
                    "agent": "browser",
                    "status": "started",
                    "message": "Interactive browser session started",
                    "url": initial_url,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            
            # Start streaming frames to the frontend as a BACKGROUND TASK
            # This allows the WebSocket handler to continue receiving user interactions
            async def stream_frames():
                """Background task to stream frames from browser-agent to frontend."""
                browser_ws_url = f"ws://browser-agent:3001/stream?session={session_id}"
                
                try:
                    async with websockets.connect(
                        browser_ws_url, 
                        ping_interval=20, 
                        ping_timeout=20,
                        max_size=10*1024*1024
                    ) as ws:
                        logger.info(f"Connected to interactive browser stream: {session_id}")
                        
                        while True:
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=30.0)
                                frame_data = json.loads(message)
                                
                                if frame_data.get("type") == "browser_frame":
                                    # Clean the base64 data
                                    image_data = frame_data.get("image", "")
                                    if image_data.startswith("data:"):
                                        image_data = image_data.split(",", 1)[1]
                                    image_data = image_data.replace('\n', '').replace('\r', '').replace(' ', '')
                                    
                                    # Extract viewport metadata for coordinate mapping
                                    metadata = frame_data.get("metadata", {})
                                    
                                    # Forward frame to frontend with viewport dimensions
                                    await connection_manager.broadcast_to_project(
                                        self.project_id,
                                        {
                                            "type": "browser_frame",
                                            "agent": "browser",
                                            "image": image_data,
                                            "format": frame_data.get("format", "jpeg"),
                                            "timestamp": datetime.utcnow().isoformat(),
                                            # Include viewport dimensions for coordinate scaling
                                            "deviceWidth": metadata.get("deviceWidth"),
                                            "deviceHeight": metadata.get("deviceHeight"),
                                            "pageScaleFactor": metadata.get("pageScaleFactor", 1),
                                        }
                                    )
                                elif frame_data.get("type") == "browser_url_changed":
                                    await connection_manager.broadcast_to_project(
                                        self.project_id,
                                        {
                                            "type": "browser_url_changed",
                                            "agent": "browser",
                                            "url": frame_data.get("url", ""),
                                            "timestamp": datetime.utcnow().isoformat(),
                                        }
                                    )
                            except asyncio.TimeoutError:
                                # Check if WebSocket is still connected
                                continue
                            except websockets.exceptions.ConnectionClosed:
                                logger.info(f"Interactive browser stream closed: {session_id}")
                                break
                                
                except Exception as stream_err:
                    logger.warning(f"Interactive browser stream error: {stream_err}")
                
                # Cleanup session from Redis
                try:
                    await redis_broadcaster._redis.delete(session_key)
                except Exception:
                    pass
            
            # Start the streaming as a background task - don't await it!
            asyncio.create_task(stream_frames())
            logger.info(f"Started background streaming task for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to start interactive browser: {e}")
            await connection_manager.send_error(
                self.project_id,
                "browser",
                str(e),
                "Failed to start interactive browser",
            )

    async def _handle_end_browser_session(self, data: Dict[str, Any]) -> None:
        """End the current browser session."""
        import httpx
        
        logger.info(f"Ending browser session for project {self.project_id}")
        
        try:
            from app.api.websocket.redis_broadcaster import redis_broadcaster
            await redis_broadcaster.connect()
            
            session_key = f"browser_session:{self.project_id}"
            session_id = await redis_broadcaster._redis.get(session_key)
            
            if session_id:
                # Delete session from browser-agent service
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.delete(f"http://browser-agent:3001/session/{session_id}")
                        logger.info(f"Closed browser session: {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to close browser session via API: {e}")
                
                # Remove from Redis
                await redis_broadcaster._redis.delete(session_key)
            
            # Notify frontend
            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "agent_status",
                    "agent": "browser",
                    "status": "completed",
                    "message": "Browser session ended",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Failed to end browser session: {e}")

    async def _handle_browser_navigation(self, data: Dict[str, Any]) -> None:
        """Handle browser navigation commands (back, forward, reload, navigate)."""
        import httpx
        
        action = data.get("action")
        url = data.get("url")
        
        logger.info(f"Browser navigation: {action}" + (f" to {url}" if url else ""))
        
        try:
            from app.api.websocket.redis_broadcaster import redis_broadcaster
            await redis_broadcaster.connect()
            
            session_key = f"browser_session:{self.project_id}"
            session_id = await redis_broadcaster._redis.get(session_key)
            
            if not session_id:
                logger.debug(f"No active browser session for project {self.project_id}")
                return
            
            # Map actions to browser-agent commands
            command_map = {
                "back": "back",
                "forward": "forward", 
                "reload": "reload",
                "navigate": "navigate",
            }
            
            command = command_map.get(action)
            if not command:
                logger.warning(f"Unknown navigation action: {action}")
                return
            
            # Send command to browser-agent
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {"command": command}
                if command == "navigate" and url:
                    payload["args"] = {"url": url}
                
                response = await client.post(
                    f"http://browser-agent:3001/session/{session_id}/command",
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"Navigation command executed: {action}")
                else:
                    logger.warning(f"Navigation failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Failed to handle browser navigation: {e}")


    async def _handle_user_interaction(self, data: Dict[str, Any]) -> None:
        """Handle user interaction event (mouse/keyboard).
        
        Since we run with multiple workers, we can't rely on in-memory tracking.
        Instead, we forward interactions via HTTP to the browser-agent service.
        """
        import httpx
        
        agent_type = data.get("agent")
        payload = data.get("payload")
        
        if agent_type != "browser":
            logger.debug(f"Ignoring non-browser interaction: {agent_type}")
            return
        
        # DEBUG LOGGING for User Interaction
        if payload and payload.get('type') == 'input_keyboard':
            logger.info(f"KEYBOARD_DEBUG: Backend received: {payload}")
            # Log specifically for 'type' events
            if payload.get('eventType') == 'type':
                logger.info(f"KEYBOARD_DEBUG: Type event with text: '{payload.get('text')}'")
        
        # Get active session for this project from Redis
        try:
            from app.api.websocket.redis_broadcaster import redis_broadcaster
            
            # Ensure Redis is connected
            await redis_broadcaster.connect()
            
            session_key = f"browser_session:{self.project_id}"
            session_id = await redis_broadcaster._redis.get(session_key)
            
            if not session_id:
                logger.debug(f"No active browser session for project {self.project_id}")
                return
            
            session_id = session_id if isinstance(session_id, str) else session_id
            
            # Use HTTP POST to send input event (avoids WebSocket connection lifecycle issues)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"http://browser-agent:3001/session/{session_id}/input",
                        json=payload
                    )
                    if response.status_code == 200:
                        logger.debug(f"Forwarded interaction to browser-agent session {session_id}: {payload.get('type')}")
                    else:
                        logger.warning(f"Browser-agent returned {response.status_code}: {response.text}")
            except Exception as http_err:
                logger.warning(f"Failed to forward interaction via HTTP: {http_err}")
                
        except Exception as e:
            logger.warning(f"Failed to handle user interaction: {e}")

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
            logger.info(f"WS raw recv: {data.get('type', 'unknown')}")
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
