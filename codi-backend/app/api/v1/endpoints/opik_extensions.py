"""Extended Opik endpoints for session grouping and trace suggestions."""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.v1.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.trace import Trace, Evaluation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/opik", tags=["Opik Extensions"])


class TraceSessionGroup(BaseModel):
    """Group of traces by session ID (user prompt)."""
    session_id: str
    user_prompt: Optional[str] = None
    total_tools: int
    success_count: int
    failure_count: int
    total_duration_ms: int
    start_time: datetime
    end_time: Optional[datetime] = None
    traces: List[Dict[str, Any]]
    

class TraceSuggestion(BaseModel):
    """Suggestion for a failed trace."""
    trace_id: str
    tool_name: str
    suggestion: str
    category: str  # e.g., "file_not_found", "permission_error", "syntax_error"


@router.get("/traces/grouped")
async def get_grouped_traces(
    project_id: int = Query(..., description="Project ID to group traces for"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get traces grouped by session_id (user prompts).
    
    Each group represents all tool executions triggered by a single user message.
    This provides a natural workflow: "I asked X, agent did Y, Z, W..."
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
    
    # Get all tool execution traces for this project
    traces_result = await db.execute(
        select(Trace).where(
            Trace.project_id == project_id,
            Trace.user_id == current_user.id,
            Trace.trace_type == 'tool_execution'
        ).order_by(Trace.start_time.asc())
    )
    traces = traces_result.scalars().all()
    
    # Group traces by session_id from meta_data
    grouped = defaultdict(list)
    for trace in traces:
        # Extract session_id from context (could be in different places)
        session_id = None
        if trace.meta_data:
            session_id = trace.meta_data.get('session_id')
        
        # Fallback: Use a default session if no session_id (shouldn't happen with new tracing)
        if not session_id:
            session_id = "unknown"
        
        grouped[session_id].append(trace)
    
    # Build session groups
    session_groups = []
    for session_id, session_traces in grouped.items():
        if not session_traces:
            continue
        
        # Calculate stats
        success_count = sum(1 for t in session_traces 
                           if t.meta_data and t.meta_data.get('status') == 'success')
        failure_count = len(session_traces) - success_count
        total_duration = sum(t.duration_ms or 0 for t in session_traces)
        
        # Get user prompt (from first trace's meta_data)
        user_prompt = None
        if session_traces[0].meta_data:
            user_prompt = session_traces[0].meta_data.get('user_prompt')
        
        # Build trace summaries
        trace_summaries = []
        for trace in session_traces:
            trace_summaries.append({
                'id': trace.id,
                'tool_name': trace.meta_data.get('tool') if trace.meta_data else trace.name,
                'status': trace.meta_data.get('status') if trace.meta_data else 'unknown',
                'duration_ms': trace.duration_ms,
                'start_time': trace.start_time.isoformat(),
                'input_data': trace.input_data,
                'output_data': trace.output_data,
            })
        
        session_groups.append(TraceSessionGroup(
            session_id=session_id,
            user_prompt=user_prompt,
            total_tools=len(session_traces),
            success_count=success_count,
            failure_count=failure_count,
            total_duration_ms=total_duration,
            start_time=session_traces[0].start_time,
            end_time=session_traces[-1].end_time if session_traces[-1].end_time else None,
            traces=trace_summaries,
        ))
    
    # Sort by start time (most recent first)
    session_groups.sort(key=lambda x: x.start_time, reverse=True)
    
    return {
        'total_sessions': len(session_groups),
        'sessions': [group.dict() for group in session_groups],
    }


@router.get("/traces/{trace_id}/suggestions")
async def get_trace_suggestions(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate actionable suggestions for a failed trace.
    
    Analyzes the error and provides context-specific recommendations.
    """
    # Get the trace
    result = await db.execute(
        select(Trace).where(
            Trace.id == trace_id,
            Trace.user_id == current_user.id
        )
    )
    trace = result.scalar_one_or_none()
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    
    # Check if trace failed
    is_failed = trace.meta_data and trace.meta_data.get('status') == 'error'
    
    if not is_failed:
        return {
            'trace_id': trace_id,
            'has_error': False,
            'suggestion': None,
        }
    
    # Extract error information
    error_message = ""
    if trace.meta_data:
        error_message = trace.meta_data.get('error', '')
    if not error_message and trace.output_data:
        error_message = trace.output_data.get('error', '')
    
    # Generate suggestion based on error pattern
    suggestion = _generate_suggestion_from_error(error_message, trace)
    
    return {
        'trace_id': trace_id,
        'has_error': True,
        'error_message': error_message,
        'suggestion': suggestion['text'],
        'category': suggestion['category'],
        'confidence': suggestion['confidence'],
    }


def _generate_suggestion_from_error(error_message: str, trace: Trace) -> Dict[str, Any]:
    """Generate a helpful suggestion based on error message."""
    error_lower = error_message.lower()
    tool_name = trace.meta_data.get('tool', 'unknown') if trace.meta_data else 'unknown'
    
    # File not found
    if 'no such file' in error_lower or 'file not found' in error_lower:
        return {
            'text': 'The file path may be incorrect. Check the path and ensure the file exists in the project.',
            'category': 'file_not_found',
            'confidence': 'high',
        }
    
    # Permission denied
    if 'permission denied' in error_lower or 'access denied' in error_lower:
        return {
            'text': 'Permission error. The file or directory may be read-only or protected.',
            'category': 'permission_error',
            'confidence': 'high',
        }
    
    # Docker errors
    if 'docker' in error_lower and ('not running' in error_lower or 'Cannot connect' in error_lower):
        return {
            'text': 'Docker is not running. Start Docker Desktop and try again.',
            'category': 'docker_not_running',
            'confidence': 'high',
        }
    
    # Port already in use
    if 'address already in use' in error_lower or 'port' in error_lower and 'already allocated' in error_lower:
        return {
            'text': 'The port is already in use by another service. Stop the conflicting service or change the port.',
            'category': 'port_conflict',
            'confidence': 'high',
        }
    
    # Syntax errors
    if 'syntax error' in error_lower or 'invalid syntax' in error_lower:
        return {
            'text': 'Syntax error in the code. Review the input for typos or formatting issues.',
            'category': 'syntax_error',
            'confidence': 'medium',
        }
    
    # Git errors
    if tool_name == 'git_commit' and ('nothing to commit' in error_lower or 'working tree clean' in error_lower):
        return {
            'text': 'No changes to commit. Make file changes before committing.',
            'category': 'git_nothing_to_commit',
            'confidence': 'high',
        }
    
    # Generic suggestion
    return {
        'text': f'Tool execution failed. Review the error details and check {tool_name} inputs.',
        'category': 'generic_error',
        'confidence': 'low',
    }
