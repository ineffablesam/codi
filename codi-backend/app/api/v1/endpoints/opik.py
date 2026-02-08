"""Opik tracing and evaluation API endpoints."""
import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.trace import Trace, Evaluation, Prompt
from app.schemas.opik import (
    TraceResponse,
    TraceListResponse,
    SummarizeCodeRequest,
    SummarizeCodeResponse,
    OpikSettingsUpdate,
    OpikSettingsResponse,
    EvaluationResponse,
)
from app.services.summarization_service import SummarizationService
from app.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/opik", tags=["Opik"])


@router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    trace_type: Optional[str] = Query(None, description="Filter by trace type"),
    min_score: Optional[float] = Query(None, description="Minimum evaluation score"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List user's traces with pagination and filtering.
    
    Only returns traces belonging to the authenticated user.
    """
    # Build query
    query = select(Trace).where(Trace.user_id == current_user.id)
    
    if project_id:
        query = query.where(Trace.project_id == project_id)
    
    if session_id:
        # Filter by session_id stored in meta_data
        query = query.where(Trace.meta_data['session_id'].astext == session_id)
    
    if trace_type:
        query = query.where(Trace.trace_type == trace_type)
    
    # Filter by minimum score (requires join with evaluations)
    if min_score is not None:
        from app.models.trace import Evaluation
        query = query.join(Evaluation, Trace.id == Evaluation.trace_id)
        query = query.where(Evaluation.score >= min_score)
    
    # Order by most recent first
    query = query.order_by(Trace.start_time.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    traces = result.scalars().all()
    
    return TraceListResponse(
        traces=[TraceResponse.model_validate(t) for t in traces],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/traces/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific trace by ID.
    
    Only accessible if the trace belongs to the authenticated user.
    """
    result = await db.execute(
        select(Trace).where(
            Trace.id == trace_id,
            Trace.user_id == current_user.id
        )
    )
    trace = result.scalar_one_or_none()
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    return TraceResponse.model_validate(trace)


@router.post("/summarize/code", response_model=SummarizeCodeResponse)
async def summarize_code(
    request: SummarizeCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Summarize code using Chain of Density method.
    
    If user has Opik tracing enabled, this creates a trace automatically.
    """
    summarization_service = SummarizationService(db)
    evaluation_service = EvaluationService(db)
    
    # Perform summarization (automatically traced if user enabled)
    summary = await summarization_service.chain_of_density_summarization(
        document=request.code,
        instruction=request.instruction,
        user_opik_enabled=current_user.opik_enabled,
        user_id=current_user.id,
        project_id=None,  # TODO: Add project_id from request when frontend sends it
        model=request.model,
        density_iterations=request.density_iterations,
    )
    
    # If tracing is enabled, save trace manually to our database
    # (Opik SDK handles cloud tracing, but we want local record too)
    trace_id = None
    quality_score = None
    quality_reason = None
    
    if current_user.opik_enabled:
        try:
            # Create trace record
            trace_id = str(uuid4())
            trace = Trace(
                id=trace_id,
                user_id=current_user.id,
                trace_type="summarization",
                name=f"Code Summary: {request.instruction[:50]}",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=0,  # Would need timing logic
                input_data={
                    "code": request.code[:500],  # Truncate for storage
                    "instruction": request.instruction,
                    "density_iterations": request.density_iterations,
                },
                output_data={"summary": summary},
                meta_data={"model": request.model},
                tags=["summarization", "code"],
            )
            db.add(trace)
            await db.commit()
            await db.refresh(trace)
            
            # Evaluate summary quality
            eval_result = await evaluation_service.evaluate_summary_quality(
                summary=summary,
                instruction=request.instruction,
                user_opik_enabled=current_user.opik_enabled,
                model=request.model,
            )
            
            quality_score = eval_result["score"]
            quality_reason = eval_result["reason"]
            
            # Save evaluation
            await evaluation_service.save_evaluation(
                trace_id=trace_id,
                metric_name="summary_quality",
                score=quality_score,
                reason=quality_reason,
                meta_data=eval_result["meta_data"],
            )
            
        except Exception as e:
            logger.warning(f"Failed to save trace/evaluation: {e}")
            # Don't fail the request, just log the error
    
    return SummarizeCodeResponse(
        summary=summary,
        trace_id=trace_id,
        quality_score=quality_score,
        quality_reason=quality_reason,
    )


@router.patch("/users/me/opik-settings", response_model=OpikSettingsResponse)
async def update_opik_settings(
    settings: OpikSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user's Opik tracing settings.
    
    Allows enabling/disabling tracing and setting workspace.
    """
    if settings.opik_enabled is not None:
        current_user.opik_enabled = settings.opik_enabled
        logger.info(f"User {current_user.id} {'enabled' if settings.opik_enabled else 'disabled'} Opik tracing")
    
    if settings.opik_workspace is not None:
        current_user.opik_workspace = settings.opik_workspace
    
    await db.commit()
    await db.refresh(current_user)
    
    return OpikSettingsResponse(
        opik_enabled=current_user.opik_enabled,
        opik_workspace=current_user.opik_workspace,
        has_api_key=current_user.opik_api_key is not None,
    )


@router.get("/users/me/opik-settings", response_model=OpikSettingsResponse)
async def get_opik_settings(
    current_user: User = Depends(get_current_user),
):
    """Get user's current Opik settings."""
    return OpikSettingsResponse(
        opik_enabled=current_user.opik_enabled,
        opik_workspace=current_user.opik_workspace,
        has_api_key=current_user.opik_api_key is not None,
    )


@router.get("/projects/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics for traces in a specific project.
    
    Returns counts, averages, success rates, and score distributions.
    """
    from app.models.project import Project
    
    # Verify user has access to this project
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id
        )
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all traces for this project
    traces_result = await db.execute(
        select(Trace).where(
            Trace.project_id == project_id,
            Trace.user_id == current_user.id
        )
    )
    traces = traces_result.scalars().all()
    
    if not traces:
        return {
            "total_traces": 0,
            "average_duration_ms": 0,
            "success_rate": 0,
            "trace_types": {},
            "score_distribution": {},
        }
    
    # Calculate statistics
    total_traces = len(traces)
    successful_traces = sum(1 for t in traces if t.meta_data and t.meta_data.get('status') == 'success')
    
    # Average duration
    durations = [t.duration_ms for t in traces if t.duration_ms is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0
    
    # Trace type distribution
    trace_types = {}
    for trace in traces:
        trace_types[trace.trace_type] = trace_types.get(trace.trace_type, 0) + 1
    
    # Get evaluation scores
    eval_result = await db.execute(
        select(Evaluation).join(Trace, Evaluation.trace_id == Trace.id).where(
            Trace.project_id == project_id,
            Trace.user_id == current_user.id
        )
    )
    evaluations = eval_result.scalars().all()
    
    # Score distribution (group by ranges)
    score_distribution = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0,
    }
    
    for evaluation in evaluations:
        score = evaluation.score
        if score < 0.2:
            score_distribution["0.0-0.2"] += 1
        elif score < 0.4:
            score_distribution["0.2-0.4"] += 1
        elif score < 0.6:
            score_distribution["0.4-0.6"] += 1
        elif score < 0.8:
            score_distribution["0.6-0.8"] += 1
        else:
            score_distribution["0.8-1.0"] += 1
    
    return {
        "total_traces": total_traces,
        "successful_traces": successful_traces,
        "success_rate": successful_traces / total_traces if total_traces > 0 else 0,
        "average_duration_ms": int(avg_duration),
        "trace_types": trace_types,
        "score_distribution": score_distribution,
        "total_evaluations": len(evaluations),
    }


@router.get("/traces/{trace_id}/details", response_model=TraceResponse)
async def get_trace_details(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed trace information including nested child traces and all evaluations.
    
    This endpoint provides a comprehensive view of a trace with all related data.
    """
    result = await db.execute(
        select(Trace).where(
            Trace.id == trace_id,
            Trace.user_id == current_user.id
        )
    )
    trace = result.scalar_one_or_none()
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # The trace model already includes evaluations and child_traces via relationships
    # They are loaded via lazy="selectin" so they're automatically fetched
    return TraceResponse.model_validate(trace)

