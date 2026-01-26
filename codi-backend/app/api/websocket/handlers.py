"""WebSocket message handlers.

Updated for Gemini 2.5 Computer Use - uses Python Playwright directly instead of Node.js browser-agent.
"""
import asyncio
import base64
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


# Track active browser agents by project_id for interaction routing
_active_browser_agents: Dict[int, Any] = {}
# Track active streaming tasks by project_id to ensure they are cancelled
_active_streaming_tasks: Dict[int, asyncio.Task] = {}


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
        elif message_type == "stop_browser_agent":
            await self._handle_stop_browser_agent(data)
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
        """Handle message routed to browser agent using Gemini 2.5 Computer Use.
        
        Args:
            message: User's request message
            data: Full message data including optional initial_url
        """
        from app.agent.computer_use_agent import ComputerUseAgent
        
        initial_url = data.get("initial_url", "https://google.com")
        
        try:
            # Create and track agent instance for interactions
            agent = ComputerUseAgent(
                project_id=self.project_id,
                user_id=self.user_id,
                headless=True,  # Run headless in production
            )
            _active_browser_agents[self.project_id] = agent
            
            # Store agent reference in Redis for cross-worker access
            try:
                from app.api.websocket.redis_broadcaster import redis_broadcaster
                await redis_broadcaster.connect()
                session_key = f"browser_session:{self.project_id}"
                await redis_broadcaster._redis.set(session_key, "computer_use_active", ex=3600)
            except Exception as e:
                logger.warning(f"Failed to store session in Redis: {e}")
            
            try:
                # Run browser agent (handles its own WebSocket broadcasting)
                await agent.run(user_message=message, initial_url=initial_url)
            finally:
                # Cleanup tracking and resources
                _active_browser_agents.pop(self.project_id, None)
                await agent.close()
                
                # Remove from Redis
                try:
                    await redis_broadcaster._redis.delete(session_key)
                except Exception:
                    pass
                
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
        Uses Python Playwright directly.
        """
        from app.agent.computer_use_agent import ComputerUseAgent, SCREEN_WIDTH, SCREEN_HEIGHT
        
        initial_url = data.get("initial_url", "https://google.com")
        
        logger.info(
            f"Starting interactive browser session",
            project_id=self.project_id,
            initial_url=initial_url,
        )
        
        try:
            # Create agent in interactive mode (no AI loop)
            agent = ComputerUseAgent(
                project_id=self.project_id,
                user_id=self.user_id,
                headless=True
            )
            
            # Initialize browser
            await agent._init_browser(initial_url)
            
            # Store agent for interaction handling
            _active_browser_agents[self.project_id] = agent
            
            # Store session in Redis
            try:
                from app.api.websocket.redis_broadcaster import redis_broadcaster
                await redis_broadcaster.connect()
                session_key = f"browser_session:{self.project_id}"
                await redis_broadcaster._redis.set(session_key, "interactive_active", ex=3600)
            except Exception as e:
                logger.warning(f"Failed to store session in Redis: {e}")
            
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
            
            # Start streaming frames in background
            async def stream_frames():
                """Background task to stream frames from Playwright to frontend."""
                frame_count = 0
                try:
                    while agent._page and not agent._stop_requested:
                        try:
                            # Capture screenshot in JPEG for speed (reduced quality for FPS)
                            start_time = datetime.utcnow()
                            screenshot_bytes = await agent._get_screenshot(format="jpeg", quality=50)
                            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                            
                            # Forward frame to frontend
                            await connection_manager.broadcast_to_project(
                                self.project_id,
                                {
                                    "type": "browser_frame",
                                    "agent": "browser",
                                    "image": screenshot_b64,
                                    "format": "jpeg",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "deviceWidth": SCREEN_WIDTH,
                                    "deviceHeight": SCREEN_HEIGHT,
                                }
                            )
                            
                            frame_count += 1
                            if frame_count % 100 == 0:
                                logger.debug(f"Streamed {frame_count} frames for project {self.project_id}")
                            
                            # Calculate sleep time to maintain ~30 FPS (33ms target)
                            elapsed = (datetime.utcnow() - start_time).total_seconds()
                            sleep_time = max(0.001, 0.033 - elapsed)
                            await asyncio.sleep(sleep_time)
                            
                        except Exception as e:
                            logger.warning(f"Frame capture error: {e}")
                            await asyncio.sleep(0.1)
                            
                except Exception as stream_err:
                    logger.warning(f"Interactive browser stream error: {stream_err}")
                finally:
                    logger.info(f"Interactive browser stream ended for project {self.project_id}")
            
            # Start the streaming as a background task
            stream_task = asyncio.create_task(stream_frames())
            _active_streaming_tasks[self.project_id] = stream_task
            logger.info(f"Started interactive browser session for project {self.project_id}")
            
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
        logger.info(f"Ending browser session for project {self.project_id}")
        
        try:
            # Get active agent
            agent = _active_browser_agents.get(self.project_id)
            
            if agent:
                # Stop and close
                agent.stop()
                await agent.close()
                _active_browser_agents.pop(self.project_id, None)
                
                # Cancel streaming task
                stream_task = _active_streaming_tasks.pop(self.project_id, None)
                if stream_task:
                    stream_task.cancel()
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass
                    logger.info(f"Cancelled streaming task for project {self.project_id}")
                    
                logger.info(f"Closed browser agent for project {self.project_id}")
            
            # Remove from Redis
            try:
                from app.api.websocket.redis_broadcaster import redis_broadcaster
                await redis_broadcaster.connect()
                session_key = f"browser_session:{self.project_id}"
                await redis_broadcaster._redis.delete(session_key)
            except Exception as e:
                logger.warning(f"Failed to remove session from Redis: {e}")
            
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

    async def _handle_stop_browser_agent(self, data: Dict[str, Any]) -> None:
        """Stop an ongoing browser agent task without closing session."""
        logger.info(f"Stopping browser agent for project {self.project_id}")
        
        agent = _active_browser_agents.get(self.project_id)
        if agent:
            agent.stop()
            
            # Cancel streaming task
            stream_task = _active_streaming_tasks.get(self.project_id)
            if stream_task:
                stream_task.cancel()
                try:
                    await stream_task
                except asyncio.CancelledError:
                    pass
                _active_streaming_tasks.pop(self.project_id, None)
                logger.info(f"Cancelled streaming task for project {self.project_id}")

            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "agent_status",
                    "agent": "browser",
                    "status": "stopped",
                    "message": "Browser agent stopped by user",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

    async def _handle_browser_navigation(self, data: Dict[str, Any]) -> None:
        """Handle browser navigation commands (back, forward, reload, navigate)."""
        action = data.get("action")
        url = data.get("url")
        
        logger.info(f"Browser navigation: {action}" + (f" to {url}" if url else ""))
        
        agent = _active_browser_agents.get(self.project_id)
        if not agent or not agent._page:
            logger.debug(f"No active browser for project {self.project_id}")
            return
        
        try:
            if action == "back":
                await agent._page.go_back()
            elif action == "forward":
                await agent._page.go_forward()
            elif action == "reload":
                await agent._page.reload()
            elif action == "navigate" and url:
                await agent._page.goto(url, wait_until="domcontentloaded")
            
            # Broadcast URL change
            current_url = agent._page.url
            await connection_manager.broadcast_to_project(
                self.project_id,
                {
                    "type": "browser_url_changed",
                    "agent": "browser",
                    "url": current_url,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to handle browser navigation: {e}")

    async def _handle_user_interaction(self, data: Dict[str, Any]) -> None:
        """Handle user interaction event (mouse/keyboard).
        
        Routes interactions directly to the Playwright browser.
        """
        agent_type = data.get("agent")
        payload = data.get("payload")
        
        if agent_type != "browser":
            logger.debug(f"Ignoring non-browser interaction: {agent_type}")
            return
        
        # Get active agent for this project
        agent = _active_browser_agents.get(self.project_id)
        
        if not agent:
            logger.debug(f"No active browser agent for project {self.project_id}")
            return
        
        try:
            await agent.handle_user_interaction({"payload": payload})
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
        
        # Update the plan status in the database
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
                        
                        # Send signal to agent via Redis
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
