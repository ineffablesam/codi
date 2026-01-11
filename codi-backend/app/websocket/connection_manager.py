"""WebSocket connection manager for real-time agent updates."""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manager for WebSocket connections to handle real-time updates."""

    _instance: Optional["ConnectionManager"] = None

    def __new__(cls) -> "ConnectionManager":
        """Singleton pattern to ensure single manager instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the connection manager."""
        if self._initialized:
            return

        # Map of project_id -> set of WebSocket connections
        self._connections: Dict[int, Set[WebSocket]] = {}

        # Map of websocket -> project_id for reverse lookup
        self._websocket_to_project: Dict[WebSocket, int] = {}

        # Lock for thread-safe operations - properly initialized lazily
        self._lock_internal: Optional[asyncio.Lock] = None

        self._initialized = True
        logger.info("WebSocket ConnectionManager initialized")

    @property
    def _lock(self) -> asyncio.Lock:
        """Get or create the lock for the current event loop."""
        if self._lock_internal is None:
            self._lock_internal = asyncio.Lock()
        return self._lock_internal

    async def connect(self, websocket: WebSocket, project_id: int) -> None:
        """Register a new WebSocket connection for a project.

        Args:
            websocket: WebSocket connection
            project_id: Project ID to subscribe to
        """
        await websocket.accept()

        async with self._lock:
            if project_id not in self._connections:
                self._connections[project_id] = set()

            self._connections[project_id].add(websocket)
            self._websocket_to_project[websocket] = project_id

        logger.info(
            f"WebSocket connected",
            project_id=project_id,
            total_connections=len(self._connections.get(project_id, set())),
        )

        # Send welcome message
        await self.send_personal_message(
            websocket,
            {
                "type": "connection_established",
                "message": "Connected to project updates",
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            project_id = self._websocket_to_project.pop(websocket, None)

            if project_id is not None and project_id in self._connections:
                self._connections[project_id].discard(websocket)

                # Clean up empty project sets
                if not self._connections[project_id]:
                    del self._connections[project_id]

                logger.info(
                    f"WebSocket disconnected",
                    project_id=project_id,
                    remaining_connections=len(self._connections.get(project_id, set())),
                )

    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: Dict[str, Any],
    ) -> None:
        """Send a message to a specific WebSocket connection.

        Args:
            websocket: Target WebSocket connection
            message: Message to send (will be JSON encoded)
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast_to_project(
        self,
        project_id: int,
        message: Dict[str, Any],
    ) -> None:
        """Broadcast a message to all connections for a project.

        Uses Redis pub/sub to enable cross-process messaging (Celery -> FastAPI).
        All messages go through Redis, and the Redis subscriber handles local delivery.

        Args:
            project_id: Project ID to broadcast to
            message: Message to send (will be JSON encoded)
        """
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        # Publish via Redis - the subscriber will handle local connections
        try:
            from app.websocket.redis_broadcaster import publish_to_websocket
            await publish_to_websocket(project_id, message)
        except Exception as e:
            logger.warning(f"Failed to publish via Redis: {e}")
            # Fallback to direct local send if Redis fails
            await self.send_to_local_connections(project_id, message)
    
    async def send_to_local_connections(
        self,
        project_id: int,
        message: Dict[str, Any],
    ) -> None:
        """Send a message directly to local WebSocket connections.
        
        This is called by the Redis subscriber when it receives a message.
        Should NOT be called directly - use broadcast_to_project instead.
        
        Args:
            project_id: Project ID to broadcast to
            message: Message to send
        """
        async with self._lock:
            connections = self._connections.get(project_id, set()).copy()

        if not connections:
            logger.debug(f"No local connections for project {project_id}")
            return

        # Send to all connections concurrently
        disconnected: List[WebSocket] = []

        async def send_to_socket(ws: WebSocket) -> None:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to websocket: {e}")
                disconnected.append(ws)

        await asyncio.gather(
            *[send_to_socket(ws) for ws in connections],
            return_exceptions=True,
        )

        # Clean up disconnected sockets
        for ws in disconnected:
            await self.disconnect(ws)

        logger.debug(
            f"Broadcast to project",
            project_id=project_id,
            message_type=message.get("type"),
            recipients=len(connections) - len(disconnected),
        )

    async def send_agent_status(
        self,
        project_id: int,
        agent: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send an agent status update to a project.

        Args:
            project_id: Project ID
            agent: Agent name
            status: Status (started, in_progress, completed, failed)
            message: Human-readable message
            details: Optional additional details
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "agent_status",
                "agent": agent,
                "status": status,
                "message": message,
                "details": details,
            },
        )

    async def send_file_operation(
        self,
        project_id: int,
        agent: str,
        operation: str,
        file_path: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a file operation update to a project.

        Args:
            project_id: Project ID
            agent: Agent name
            operation: Operation (create, update, delete)
            file_path: Path to the file
            message: Human-readable message
            details: Optional additional details (lines_of_code, widgets, etc.)
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "file_operation",
                "agent": agent,
                "operation": operation,
                "file_path": file_path,
                "message": message,
                "details": details,
            },
        )

    async def send_tool_execution(
        self,
        project_id: int,
        agent: str,
        tool: str,
        message: str,
        file_path: Optional[str] = None,
    ) -> None:
        """Send a tool execution update to a project.

        Args:
            project_id: Project ID
            agent: Agent name
            tool: Tool name
            message: Human-readable message
            file_path: Optional file path involved
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "tool_execution",
                "agent": agent,
                "tool": tool,
                "file_path": file_path,
                "message": message,
            },
        )

    async def send_git_operation(
        self,
        project_id: int,
        operation: str,
        message: str,
        branch_name: Optional[str] = None,
        commit_sha: Optional[str] = None,
        files_changed: Optional[int] = None,
        insertions: Optional[int] = None,
        deletions: Optional[int] = None,
    ) -> None:
        """Send a git operation update to a project.

        Args:
            project_id: Project ID
            operation: Git operation (create_branch, commit, push, merge)
            message: Human-readable message
            branch_name: Branch name involved
            commit_sha: Commit SHA if applicable
            files_changed: Number of files changed
            insertions: Number of line insertions
            deletions: Number of line deletions
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "git_operation",
                "agent": "git_operator",
                "operation": operation,
                "branch_name": branch_name,
                "commit_sha": commit_sha,
                "message": message,
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
            },
        )

    async def send_build_progress(
        self,
        project_id: int,
        stage: str,
        message: str,
        progress: float,
    ) -> None:
        """Send a build progress update to a project.

        Args:
            project_id: Project ID
            stage: Build stage (dependencies, build, test, deploy)
            message: Human-readable message
            progress: Progress value (0.0 to 1.0)
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "build_progress",
                "agent": "build_deploy",
                "stage": stage,
                "message": message,
                "progress": min(max(progress, 0.0), 1.0),
            },
        )

    async def send_deployment_complete(
        self,
        project_id: int,
        status: str,
        message: str,
        deployment_url: Optional[str] = None,
        build_time: Optional[str] = None,
        size: Optional[str] = None,
    ) -> None:
        """Send a deployment complete update to a project.

        Args:
            project_id: Project ID
            status: Deployment status (success, failed)
            message: Human-readable message
            deployment_url: URL of the deployed app
            build_time: Build duration string
            size: Build size string
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "deployment_complete",
                "agent": "build_deploy",
                "status": status,
                "deployment_url": deployment_url,
                "message": message,
                "details": {
                    "build_time": build_time,
                    "size": size,
                },
            },
        )

    async def send_error(
        self,
        project_id: int,
        agent: str,
        error: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send an error message to a project.

        Args:
            project_id: Project ID
            agent: Agent that encountered the error
            error: Error description
            message: Human-readable message
            details: Optional additional details
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "agent_error",
                "agent": agent,
                "error": error,
                "message": message,
                "details": details,
            },
        )

    async def send_user_input_required(
        self,
        project_id: int,
        agent: str,
        question: str,
        options: Optional[List[str]] = None,
    ) -> None:
        """Request user input via WebSocket.

        Args:
            project_id: Project ID
            agent: Agent requesting input
            question: Question to ask the user
            options: Optional list of suggested options
        """
        await self.broadcast_to_project(
            project_id,
            {
                "type": "user_input_required",
                "agent": agent,
                "question": question,
                "options": options,
            },
        )

    def get_connection_count(self, project_id: Optional[int] = None) -> int:
        """Get the number of active connections.

        Args:
            project_id: Optional project ID to filter by

        Returns:
            Number of active connections
        """
        if project_id is not None:
            return len(self._connections.get(project_id, set()))
        return sum(len(conns) for conns in self._connections.values())

    def get_active_projects(self) -> List[int]:
        """Get list of project IDs with active connections.

        Returns:
            List of project IDs
        """
        return list(self._connections.keys())


# Global connection manager instance
connection_manager = ConnectionManager()
