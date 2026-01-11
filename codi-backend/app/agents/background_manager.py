"""Background Manager for parallel task execution.

Enables parallel background task execution with concurrency control,
session continuity, and task completion notifications.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from app.config import settings
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager
from app.agents.types import (
    BackgroundTask,
    LaunchInput,
    ResumeInput,
    TaskProgress,
    TaskStatus,
)

logger = get_logger(__name__)

# Task TTL - tasks older than this are pruned
TASK_TTL = timedelta(minutes=30)

# Poll interval for checking task status
POLL_INTERVAL_SECONDS = 2


class ConcurrencyManager:
    """Manages concurrent access to agent resources."""
    
    def __init__(self, max_per_agent: int = 3, max_total: int = 10):
        self.max_per_agent = max_per_agent
        self.max_total = max_total
        self._locks: Dict[str, int] = {}  # agent_name -> count
        self._total_count = 0
        self._lock = asyncio.Lock()
        self._waiting: Dict[str, asyncio.Event] = {}
    
    async def acquire(self, agent_name: str) -> None:
        """Acquire a slot for an agent. Blocks if limit reached."""
        async with self._lock:
            while (
                self._locks.get(agent_name, 0) >= self.max_per_agent or
                self._total_count >= self.max_total
            ):
                # Create a wait event
                event = asyncio.Event()
                self._waiting[f"{agent_name}_{id(event)}"] = event
                self._lock.release()
                await event.wait()
                await self._lock.acquire()
            
            self._locks[agent_name] = self._locks.get(agent_name, 0) + 1
            self._total_count += 1
            logger.debug(f"Acquired slot for {agent_name}: {self._locks[agent_name]}/{self.max_per_agent}")
    
    def release(self, agent_name: str) -> None:
        """Release a slot for an agent."""
        if agent_name in self._locks and self._locks[agent_name] > 0:
            self._locks[agent_name] -= 1
            self._total_count -= 1
            logger.debug(f"Released slot for {agent_name}: {self._locks[agent_name]}/{self.max_per_agent}")
            
            # Wake up any waiting tasks
            for key, event in list(self._waiting.items()):
                event.set()
                del self._waiting[key]
                break  # Only wake one


class BackgroundManager:
    """Manager for background task execution.
    
    Features:
    - Launch async background tasks with concurrency control
    - Poll for task completion via status checks
    - Resume previous sessions with context preservation
    - Handle task notifications to parent sessions
    - TTL-based cleanup (30 min default)
    """
    
    _instance: Optional["BackgroundManager"] = None
    
    def __new__(cls) -> "BackgroundManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tasks: Dict[str, BackgroundTask] = {}
        self._notifications: Dict[str, List[BackgroundTask]] = {}  # parent_session_id -> tasks
        self._concurrency_manager = ConcurrencyManager()
        self._polling_task: Optional[asyncio.Task] = None
        self._active_sessions: Set[str] = set()
        self._initialized = True
        
        logger.info("BackgroundManager initialized")
    
    async def launch(self, input: LaunchInput) -> BackgroundTask:
        """Launch a new background task.
        
        Args:
            input: LaunchInput with task configuration
            
        Returns:
            BackgroundTask instance
        """
        if not input.agent or not input.agent.strip():
            raise ValueError("Agent parameter is required")
        
        concurrency_key = input.agent
        
        # Acquire concurrency slot
        await self._concurrency_manager.acquire(concurrency_key)
        
        # Generate unique IDs
        task_id = f"bg_{uuid.uuid4().hex[:8]}"
        session_id = f"ses_{uuid.uuid4().hex[:12]}"
        
        # Create task
        task = BackgroundTask(
            id=task_id,
            session_id=session_id,
            parent_session_id=input.parent_session_id,
            description=input.description,
            prompt=input.prompt,
            agent=input.agent,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow(),
            parent_agent=input.parent_agent,
            parent_model=input.parent_model,
            concurrency_key=concurrency_key,
            category=input.category,
            skills=input.skills or [],
        )
        
        self._tasks[task_id] = task
        self._active_sessions.add(session_id)
        
        logger.info(f"Launching background task: {task_id} agent={input.agent}")
        
        # Notify via WebSocket
        await self._broadcast_task_started(task)
        
        # Start polling if not already running
        self._start_polling()
        
        # Launch the actual agent execution in background
        asyncio.create_task(self._execute_task(task, input))
        
        return task
    
    async def _execute_task(self, task: BackgroundTask, input: LaunchInput) -> None:
        """Execute a background task asynchronously."""
        try:
            # Import here to avoid circular imports
            from app.workflows.executor import WorkflowExecutor
            
            # TODO: This will be replaced with proper agent delegation
            # For now, we'll mark as completed after a simulated delay
            # In the full implementation, this calls the appropriate agent
            
            logger.info(f"Executing background task {task.id} with agent {task.agent}")
            
            # Update progress
            task.progress.tool_calls += 1
            task.progress.last_tool = "initialize"
            task.progress.last_update = datetime.utcnow()
            
            await self._broadcast_task_progress(task)
            
            # Placeholder for actual execution
            # The real implementation will call the agent graph
            await asyncio.sleep(0.1)  # Small delay to simulate work start
            
            # Mark as completed (real implementation will be triggered by agent completion)
            # task.status = TaskStatus.COMPLETED
            # task.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Background task {task.id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
            if task.concurrency_key:
                self._concurrency_manager.release(task.concurrency_key)
            
            await self._broadcast_task_completed(task)
            self._mark_for_notification(task)
    
    async def resume(self, input: ResumeInput) -> BackgroundTask:
        """Resume an existing task with new prompt.
        
        Args:
            input: ResumeInput with session ID and new prompt
            
        Returns:
            Resumed BackgroundTask
        """
        task = self.find_by_session(input.session_id)
        if not task:
            raise ValueError(f"Task not found for session: {input.session_id}")
        
        # Reset task state
        task.status = TaskStatus.RUNNING
        task.completed_at = None
        task.error = None
        task.parent_session_id = input.parent_session_id
        task.parent_agent = input.parent_agent
        task.parent_model = input.parent_model
        task.progress = TaskProgress(
            tool_calls=task.progress.tool_calls,
            last_update=datetime.utcnow()
        )
        
        self._active_sessions.add(task.session_id)
        self._start_polling()
        
        logger.info(f"Resuming task {task.id} with session {task.session_id}")
        
        await self._broadcast_task_started(task)
        
        return task
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def find_by_session(self, session_id: str) -> Optional[BackgroundTask]:
        """Find a task by session ID."""
        for task in self._tasks.values():
            if task.session_id == session_id:
                return task
        return None
    
    def get_tasks_by_parent(self, parent_session_id: str) -> List[BackgroundTask]:
        """Get all tasks spawned by a parent session."""
        return [
            task for task in self._tasks.values()
            if task.parent_session_id == parent_session_id
        ]
    
    def get_running_tasks(self) -> List[BackgroundTask]:
        """Get all currently running tasks."""
        return [
            task for task in self._tasks.values()
            if task.status == TaskStatus.RUNNING
        ]
    
    async def cancel(self, task_id: str) -> bool:
        """Cancel a specific task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancelled, False if not found
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        task.error = "Cancelled by user"
        
        if task.concurrency_key:
            self._concurrency_manager.release(task.concurrency_key)
        
        self._active_sessions.discard(task.session_id)
        
        logger.info(f"Cancelled task {task_id}")
        
        await self._broadcast_task_completed(task)
        
        return True
    
    async def cancel_all(self, parent_session_id: Optional[str] = None) -> int:
        """Cancel all tasks, optionally filtered by parent session.
        
        Args:
            parent_session_id: If provided, only cancel tasks for this parent
            
        Returns:
            Number of tasks cancelled
        """
        cancelled = 0
        tasks_to_cancel = []
        
        for task in self._tasks.values():
            if task.status != TaskStatus.RUNNING:
                continue
            if parent_session_id and task.parent_session_id != parent_session_id:
                continue
            tasks_to_cancel.append(task.id)
        
        for task_id in tasks_to_cancel:
            if await self.cancel(task_id):
                cancelled += 1
        
        logger.info(f"Cancelled {cancelled} background tasks")
        return cancelled
    
    def complete_task(self, task_id: str, result: Optional[str] = None) -> None:
        """Mark a task as completed.
        
        Called when an agent finishes execution.
        
        Args:
            task_id: Task ID
            result: Optional result text
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for completion")
            return
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = result
        
        if task.concurrency_key:
            self._concurrency_manager.release(task.concurrency_key)
        
        self._active_sessions.discard(task.session_id)
        self._mark_for_notification(task)
        
        logger.info(f"Task {task_id} completed")
        
        # Schedule async notification
        asyncio.create_task(self._broadcast_task_completed(task))
    
    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed.
        
        Args:
            task_id: Task ID
            error: Error message
        """
        task = self._tasks.get(task_id)
        if not task:
            return
        
        task.status = TaskStatus.FAILED
        task.completed_at = datetime.utcnow()
        task.error = error
        
        if task.concurrency_key:
            self._concurrency_manager.release(task.concurrency_key)
        
        self._active_sessions.discard(task.session_id)
        self._mark_for_notification(task)
        
        logger.error(f"Task {task_id} failed: {error}")
        
        asyncio.create_task(self._broadcast_task_completed(task))
    
    def _mark_for_notification(self, task: BackgroundTask) -> None:
        """Mark a task for notification to parent session."""
        parent_id = task.parent_session_id
        if parent_id not in self._notifications:
            self._notifications[parent_id] = []
        self._notifications[parent_id].append(task)
    
    def get_pending_notifications(self, parent_session_id: str) -> List[BackgroundTask]:
        """Get pending notifications for a parent session."""
        return self._notifications.get(parent_session_id, [])
    
    def clear_notifications(self, parent_session_id: str) -> None:
        """Clear notifications for a parent session."""
        self._notifications.pop(parent_session_id, None)
    
    def _start_polling(self) -> None:
        """Start the polling task if not already running."""
        if self._polling_task is None or self._polling_task.done():
            self._polling_task = asyncio.create_task(self._poll_loop())
    
    async def _poll_loop(self) -> None:
        """Polling loop for task status and cleanup."""
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            
            # Prune stale tasks
            self._prune_stale_tasks()
            
            # Check if we still have running tasks
            if not self.get_running_tasks():
                logger.debug("No running tasks, stopping poll loop")
                break
    
    def _prune_stale_tasks(self) -> None:
        """Remove tasks older than TTL."""
        now = datetime.utcnow()
        stale_ids = []
        
        for task_id, task in self._tasks.items():
            age = now - task.started_at
            if age > TASK_TTL:
                stale_ids.append(task_id)
                if task.concurrency_key:
                    self._concurrency_manager.release(task.concurrency_key)
        
        for task_id in stale_ids:
            task = self._tasks.pop(task_id, None)
            if task:
                self._active_sessions.discard(task.session_id)
                logger.info(f"Pruned stale task {task_id}")
    
    async def _broadcast_task_started(self, task: BackgroundTask) -> None:
        """Broadcast task started via WebSocket."""
        # Extract project_id from parent_session_id if it contains it
        # For now, we'll need to look this up or pass it differently
        try:
            # Try to parse project_id from session context
            # This is a placeholder - real implementation needs proper project tracking
            await connection_manager.broadcast_to_project(
                project_id=0,  # TODO: Get proper project ID
                message={
                    "type": "background_task_started",
                    "task_id": task.id,
                    "session_id": task.session_id,
                    "description": task.description,
                    "agent": task.agent,
                    "category": task.category,
                }
            )
        except Exception as e:
            logger.debug(f"Could not broadcast task started: {e}")
    
    async def _broadcast_task_progress(self, task: BackgroundTask) -> None:
        """Broadcast task progress via WebSocket."""
        try:
            await connection_manager.broadcast_to_project(
                project_id=0,  # TODO: Get proper project ID
                message={
                    "type": "background_task_progress",
                    "task_id": task.id,
                    "progress": {
                        "tool_calls": task.progress.tool_calls,
                        "last_tool": task.progress.last_tool,
                    }
                }
            )
        except Exception as e:
            logger.debug(f"Could not broadcast task progress: {e}")
    
    async def _broadcast_task_completed(self, task: BackgroundTask) -> None:
        """Broadcast task completed via WebSocket."""
        duration = self._format_duration(task.started_at, task.completed_at)
        try:
            await connection_manager.broadcast_to_project(
                project_id=0,  # TODO: Get proper project ID
                message={
                    "type": "background_task_completed",
                    "task_id": task.id,
                    "status": task.status.value,
                    "duration": duration,
                    "error": task.error,
                }
            )
        except Exception as e:
            logger.debug(f"Could not broadcast task completed: {e}")
    
    @staticmethod
    def _format_duration(start: datetime, end: Optional[datetime]) -> str:
        """Format duration as human-readable string."""
        if end is None:
            end = datetime.utcnow()
        
        duration = end - start
        seconds = int(duration.total_seconds())
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            return f"{hours}h {minutes % 60}m {seconds % 60}s"
        elif minutes > 0:
            return f"{minutes}m {seconds % 60}s"
        return f"{seconds}s"
    
    def cleanup(self) -> None:
        """Cleanup all tasks and stop polling."""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
        
        self._tasks.clear()
        self._notifications.clear()
        self._active_sessions.clear()
        
        logger.info("BackgroundManager cleaned up")


# Global singleton instance
background_manager = BackgroundManager()
