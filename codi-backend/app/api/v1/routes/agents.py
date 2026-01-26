"""Agents API endpoints for triggering and monitoring agent tasks."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.database import get_db_session, get_db_context
from app.models.project import Project
from app.models.user import User
from app.models.agent_task import AgentTask
from app.schemas.agent import AgentTaskRequest, AgentTaskResponse, AgentTaskStatus
from app.utils.logging import get_logger
from app.utils.security import TokenPayload
from app.api.websocket.connection_manager import connection_manager
from app.api.websocket.handlers import websocket_endpoint_handler

import hashlib
from datetime import datetime, timedelta

logger = get_logger(__name__)

# Simple in-memory cache for idempotency (safety net for duplicate clicks/triggers)
# (project_id, message_hash) -> (task_id, timestamp)
_recent_tasks = {}

def _get_message_hash(message: str) -> str:
    return hashlib.md5(message.strip().encode()).hexdigest()

def _check_idempotency(project_id: int, message: str) -> Optional[str]:
    now = datetime.utcnow()
    msg_hash = _get_message_hash(message)
    key = (project_id, msg_hash)
    
    if key in _recent_tasks:
        task_id, timestamp = _recent_tasks[key]
        # Ignore duplicates within 2 seconds
        if now - timestamp < timedelta(seconds=2):
            logger.info(f"Duplicate task submission detected, returning existing task_id: {task_id}")
            return task_id
            
    # Cleanup old entries every 10 seconds to keep memory low
    for k in list(_recent_tasks.keys()):
        if now - _recent_tasks[k][1] > timedelta(seconds=30):
            del _recent_tasks[k]
            
    return None

def _record_task(project_id: int, message: str, task_id: str):
    msg_hash = _get_message_hash(message)
    _recent_tasks[(project_id, msg_hash)] = (task_id, datetime.utcnow())

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/{project_id}/task", response_model=AgentTaskResponse)
async def submit_agent_task(
    project_id: int,
    task_request: AgentTaskRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentTaskResponse:
    """Submit a task for the agent workflow to process.

    Args:
        project_id: Project ID
        task_request: Task request with user message
        session: Database session
        current_user: Authenticated user

    Returns:
        Task response with task ID
    """
    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Check for duplicate submission (idempotency)
    existing_task_id = _check_idempotency(project_id, task_request.message)
    if existing_task_id:
        return AgentTaskResponse(
            task_id=existing_task_id,
            status="queued",
            message="Duplicate task; returning existing task info",
        )

    # Generate task ID
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    _record_task(project_id, task_request.message, task_id)

    # Persist the task in the database
    agent_task = AgentTask(
        id=task_id,
        project_id=project_id,
        user_id=current_user.id,
        status="queued",
        message=task_request.message,
    )
    session.add(agent_task)
    await session.commit()

    # Queue the task with local project folder
    try:
        from app.tasks.celery_app import run_agent_workflow_task

        # Submit to Celery with local project folder
        celery_result = run_agent_workflow_task.delay(
            task_id=task_id,
            project_id=project_id,
            user_id=current_user.id,
            user_message=task_request.message,
            project_folder=project.local_path,
        )

        # Update task with Celery ID
        agent_task.celery_task_id = celery_result.id
        await session.commit()

        logger.info(
            f"Agent task submitted",
            task_id=task_id,
            project_id=project_id,
            celery_task_id=celery_result.id,
        )

        return AgentTaskResponse(
            task_id=task_id,
            status="queued",
            message="Task submitted successfully",
        )

    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        return AgentTaskResponse(
            task_id=task_id,
            status="error",
            message=f"Failed to submit task: {str(e)}",
            created_at=datetime.now(timezone.utc),
        )


async def submit_agent_task_internal(
    project_id: int,
    user_id: int,
    message: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Internal function to submit agent task (used by WebSocket handler).

    Args:
        project_id: Project ID
        user_id: User ID
        message: User message
        session_id: Optional chat session ID for multi-chat

    Returns:
        Task submission result
    """
    # Check for duplicate submission (idempotency)
    existing_task_id = _check_idempotency(project_id, message)
    if existing_task_id:
        return {"task_id": existing_task_id, "status": "queued"}

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    _record_task(project_id, message, task_id)

    # Get project's local path
    async with get_db_context() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id,
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            return {"task_id": task_id, "status": "error", "message": "Project not found"}

        project_folder = project.local_path

        # Persist the task in the database
        agent_task = AgentTask(
            id=task_id,
            project_id=project_id,
            user_id=user_id,
            status="queued",
            message=message,
        )
        session.add(agent_task)
        await session.commit()

    try:
        from app.tasks.celery_app import run_agent_workflow_task

        celery_result = run_agent_workflow_task.delay(
            task_id=task_id,
            project_id=project_id,
            user_id=user_id,
            user_message=message,
            project_folder=project_folder,
            session_id=session_id,  # Pass session_id for multi-chat
        )

        # Update task with Celery ID
        async with get_db_context() as session:
            await session.execute(
                update(AgentTask)
                .where(AgentTask.id == task_id)
                .values(celery_task_id=celery_result.id)
            )
            await session.commit()

        return {"task_id": task_id, "status": "queued", "session_id": session_id}

    except Exception as e:
        return {"task_id": task_id, "status": "error", "message": str(e)}


@router.get("/{project_id}/task/{task_id}", response_model=AgentTaskStatus)
async def get_task_status(
    project_id: int,
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AgentTaskStatus:
    """Get the status of an agent task.

    Args:
        project_id: Project ID
        task_id: Task ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Task status
    """
    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get task status from DB
    result = await session.execute(
        select(AgentTask).where(
            AgentTask.id == task_id,
            AgentTask.project_id == project_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return AgentTaskStatus(
        task_id=task.id,
        status=task.status,
        progress=task.progress / 100.0 if task.progress is not None else 0.0,
        message=task.message,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error=task.error,
    )


@router.websocket("/{project_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    project_id: int,
) -> None:
    """WebSocket endpoint for real-time agent updates.

    Args:
        websocket: WebSocket connection
        project_id: Project ID to subscribe to
    """
    # Authenticate from query params or headers
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    # Validate token
    payload = TokenPayload.from_token(token)

    if payload is None or payload.is_expired():
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = payload.user_id
    if user_id is None:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # Verify project access
    async with get_db_context() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == user_id,
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            await websocket.close(code=4004, reason="Project not found")
            return

    # Handle WebSocket messages
    await websocket_endpoint_handler(websocket, project_id, user_id)


@router.get("/{project_id}/history")
async def get_operation_history(
    project_id: int,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get operation history for a project.

    Args:
        project_id: Project ID
        limit: Maximum operations to return
        session: Database session
        current_user: Authenticated user

    Returns:
        List of recent operations
    """
    from app.models.operation_log import OperationLog

    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get operations
    result = await session.execute(
        select(OperationLog)
        .where(OperationLog.project_id == project_id)
        .order_by(OperationLog.created_at.desc())
        .limit(limit)
    )
    operations = result.scalars().all()

    return {
        "operations": [op.to_websocket_message() for op in operations],
        "total": len(operations),
    }


@router.post("/{project_id}/task/{task_id}/stop")
async def stop_agent_task(
    project_id: int,
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Stop/Cancel a running agent task.

    Args:
        project_id: Project ID
        task_id: Task ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Status message
    """
    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Get task
    result = await session.execute(
        select(AgentTask).where(
            AgentTask.id == task_id,
            AgentTask.project_id == project_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if task.status not in ["queued", "processing"]:
        return {"message": f"Task is already in {task.status} state"}

    # Revoke Celery task if it exists
    if task.celery_task_id:
        from app.tasks.celery_app import celery_app
        logger.info(f"Revoking Celery task: {task.celery_task_id}")
        celery_app.control.revoke(task.celery_task_id, terminate=True, signal='SIGKILL')

    # Update state in DB
    task.status = "failed"
    task.error = "Task stopped by user"
    task.completed_at = datetime.utcnow()
    await session.commit()

    # Broadcast status update
    await connection_manager.broadcast_to_project(
        project_id,
        {
            "type": "agent_status",
            "agent": "codi",
            "status": "failed",
            "message": "Task stopped by user",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    return {"message": "Task stop signal sent"}
