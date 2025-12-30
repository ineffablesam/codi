"""Agents API endpoints for triggering and monitoring agent tasks."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_github_token
from app.database import get_db_session, get_db_context
from app.models.project import Project
from app.models.user import User
from app.models.agent_task import AgentTask
from app.schemas.agent import AgentTaskRequest, AgentTaskResponse, AgentTaskStatus
from app.services.encryption import encryption_service
from app.utils.logging import get_logger
from app.utils.security import TokenPayload
from app.websocket.connection_manager import connection_manager
from app.websocket.handlers import websocket_endpoint_handler

logger = get_logger(__name__)
router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/{project_id}/task", response_model=AgentTaskResponse)
async def submit_agent_task(
    project_id: int,
    task_request: AgentTaskRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> AgentTaskResponse:
    """Submit a task for the agent workflow to process.

    Args:
        project_id: Project ID
        task_request: Task request with user message
        session: Database session
        current_user: Authenticated user
        github_token: GitHub access token

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

    # Generate task ID
    task_id = f"task_{uuid.uuid4().hex[:12]}"

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

    # Queue the task (in production, this goes to Celery)
    try:
        from app.tasks.celery_app import run_agent_workflow_task

        # Get encrypted token
        encrypted_token = current_user.github_access_token_encrypted

        # Submit to Celery
        celery_result = run_agent_workflow_task.delay(
            task_id=task_id,
            project_id=project_id,
            user_id=current_user.id,
            user_message=task_request.message,
            github_token_encrypted=encrypted_token,
        )

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
        # Fall back to sync notification
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
) -> Dict[str, Any]:
    """Internal function to submit agent task (used by WebSocket handler).

    Args:
        project_id: Project ID
        user_id: User ID
        message: User message

    Returns:
        Task submission result
    """
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    # Get user's encrypted token
    async with get_db_context() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.github_access_token_encrypted:
            return {"task_id": task_id, "status": "error", "message": "No GitHub token"}

        encrypted_token = user.github_access_token_encrypted

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

        run_agent_workflow_task.delay(
            task_id=task_id,
            project_id=project_id,
            user_id=user_id,
            user_message=message,
            github_token_encrypted=encrypted_token,
        )

        return {"task_id": task_id, "status": "queued"}

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
        current_agent=task.current_agent,
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
