"""API endpoints for implementation plan management.

NOTE: This has been simplified to work with the new baby-code style agent.
Plans are now created directly via the simple coding agent rather than
a dedicated PlannerAgent.
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.agent.tools import AgentContext
from app.core.database import get_db
from app.models.plan import ImplementationPlan, PlanStatus, PlanTask
from app.models.project import Project
from app.models.user import User
from app.schemas.plan import (
    ApproveRejectRequest,
    CreatePlanRequest,
    MarkdownResponse,
    PlanListResponse,
    PlanResponse,
    TaskResponse,
    UpdateTaskRequest,
)
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: CreatePlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """
    Create a new implementation plan from user request.

    This creates a simple plan record. The actual implementation
    is now handled by the unified coding agent via chat.
    """
    # Verify project exists and user has access
    result = await db.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )

    try:
        # Create a simple plan record
        plan = ImplementationPlan(
            project_id=project.id,
            title=f"Plan: {request.user_request[:50]}...",
            user_request=request.user_request,
            status=PlanStatus.PENDING_REVIEW,
            estimated_time="Estimated by agent",
            total_tasks=0,
            completed_tasks=0,
            markdown_content=f"# Implementation Plan\n\n{request.user_request}\n\n*Use the chat to implement this request.*",
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        return PlanResponse(
            id=plan.id,
            project_id=plan.project_id,
            title=plan.title,
            user_request=plan.user_request,
            status=plan.status.value if isinstance(plan.status, PlanStatus) else plan.status,
            estimated_time=plan.estimated_time,
            total_tasks=plan.total_tasks,
            completed_tasks=plan.completed_tasks,
            progress=plan.progress,
            file_path=plan.file_path,
            walkthrough_path=plan.walkthrough_path,
            created_at=plan.created_at,
            approved_at=plan.approved_at,
            rejected_at=plan.rejected_at,
            completed_at=plan.completed_at,
            tasks=[],
        )

    except Exception as e:
        logger.error(f"Failed to create plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan: {str(e)}",
        )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Get a specific implementation plan by ID."""
    result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Verify user has access to this project
    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return PlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        user_request=plan.user_request,
        status=plan.status.value if isinstance(plan.status, PlanStatus) else plan.status,
        estimated_time=plan.estimated_time,
        total_tasks=plan.total_tasks,
        completed_tasks=plan.completed_tasks,
        progress=plan.progress,
        file_path=plan.file_path,
        walkthrough_path=plan.walkthrough_path,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        rejected_at=plan.rejected_at,
        completed_at=plan.completed_at,
        tasks=[TaskResponse.model_validate(t) for t in plan.tasks],
    )


@router.get("/project/{project_id}", response_model=List[PlanListResponse])
async def get_project_plans(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[PlanListResponse]:
    """Get all implementation plans for a project."""
    # Verify user has access
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or access denied",
        )

    result = await db.execute(
        select(ImplementationPlan)
        .where(ImplementationPlan.project_id == project_id)
        .order_by(ImplementationPlan.created_at.desc())
    )
    plans = result.scalars().all()

    return [
        PlanListResponse(
            id=p.id,
            project_id=p.project_id,
            title=p.title,
            user_request=p.user_request,
            status=p.status.value if isinstance(p.status, PlanStatus) else p.status,
            estimated_time=p.estimated_time,
            total_tasks=p.total_tasks,
            completed_tasks=p.completed_tasks,
            progress=p.progress,
            created_at=p.created_at,
            completed_at=p.completed_at,
        )
        for p in plans
    ]


@router.post("/{plan_id}/approve", response_model=PlanResponse)
async def approve_plan(
    plan_id: int,
    request: ApproveRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Approve an implementation plan."""
    result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Verify user has access
    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    current_status = plan.status.value if isinstance(plan.status, PlanStatus) else plan.status
    if current_status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve plan with status: {current_status}",
        )

    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)

    # Send WebSocket notification
    await connection_manager.broadcast_to_project(
        plan.project_id,
        {
            "type": "plan_approved",
            "plan_id": plan_id,
            "message": request.comment or "Plan approved.",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    return PlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        user_request=plan.user_request,
        status=plan.status.value if isinstance(plan.status, PlanStatus) else plan.status,
        estimated_time=plan.estimated_time,
        total_tasks=plan.total_tasks,
        completed_tasks=plan.completed_tasks,
        progress=plan.progress,
        file_path=plan.file_path,
        walkthrough_path=plan.walkthrough_path,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        rejected_at=plan.rejected_at,
        completed_at=plan.completed_at,
        tasks=[TaskResponse.model_validate(t) for t in plan.tasks],
    )


@router.post("/{plan_id}/reject", response_model=PlanResponse)
async def reject_plan(
    plan_id: int,
    request: ApproveRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PlanResponse:
    """Reject an implementation plan."""
    result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Verify user has access
    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    current_status = plan.status.value if isinstance(plan.status, PlanStatus) else plan.status
    if current_status != "pending_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject plan with status: {current_status}",
        )

    plan.status = PlanStatus.REJECTED
    plan.rejected_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)

    # Send WebSocket notification
    await connection_manager.broadcast_to_project(
        plan.project_id,
        {
            "type": "plan_rejected",
            "plan_id": plan_id,
            "message": request.comment or "Plan declined.",
            "timestamp": datetime.utcnow().isoformat(),
        },
    )

    return PlanResponse(
        id=plan.id,
        project_id=plan.project_id,
        title=plan.title,
        user_request=plan.user_request,
        status=plan.status.value if isinstance(plan.status, PlanStatus) else plan.status,
        estimated_time=plan.estimated_time,
        total_tasks=plan.total_tasks,
        completed_tasks=plan.completed_tasks,
        progress=plan.progress,
        file_path=plan.file_path,
        walkthrough_path=plan.walkthrough_path,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        rejected_at=plan.rejected_at,
        completed_at=plan.completed_at,
        tasks=[TaskResponse.model_validate(t) for t in plan.tasks],
    )


@router.get("/{plan_id}/tasks", response_model=List[TaskResponse])
async def get_plan_tasks(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[TaskResponse]:
    """Get all tasks for a plan."""
    # Verify access
    plan_result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    result = await db.execute(
        select(PlanTask)
        .where(PlanTask.plan_id == plan_id)
        .order_by(PlanTask.order_index)
    )
    tasks = result.scalars().all()

    return [TaskResponse.model_validate(task) for task in tasks]


@router.patch("/{plan_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    plan_id: int,
    task_id: int,
    request: UpdateTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update task completion status."""
    # Verify access
    plan_result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    try:
        # Update task status
        task_result = await db.execute(
            select(PlanTask).where(PlanTask.id == task_id)
        )
        task = task_result.scalar_one_or_none()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found",
            )
        
        task.is_completed = request.completed
        await db.commit()
        await db.refresh(task)

        return TaskResponse.model_validate(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )


@router.get("/{plan_id}/markdown", response_model=MarkdownResponse)
async def get_plan_markdown(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkdownResponse:
    """Get the raw markdown content of a plan."""
    result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Verify access
    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return MarkdownResponse(
        markdown=plan.markdown_content,
        file_path=plan.file_path,
    )


@router.get("/{plan_id}/walkthrough", response_model=MarkdownResponse)
async def get_walkthrough(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkdownResponse:
    """Get the walkthrough content for a completed plan."""
    result = await db.execute(
        select(ImplementationPlan).where(ImplementationPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    # Verify access
    project_result = await db.execute(
        select(Project).where(
            Project.id == plan.project_id,
            Project.owner_id == current_user.id,
        )
    )
    if not project_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not plan.walkthrough_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Walkthrough not yet generated",
        )

    # Read walkthrough file
    try:
        from pathlib import Path
        content = Path(plan.walkthrough_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read walkthrough: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read walkthrough file",
        )

    return MarkdownResponse(
        markdown=content,
        file_path=plan.walkthrough_path,
    )
