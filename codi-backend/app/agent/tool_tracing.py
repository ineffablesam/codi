"""Tool tracing decorator for automatic Opik integration.

This module provides a decorator that automatically traces all tool executions
with Opik, capturing detailed metadata about each tool call including inputs,
outputs, errors, and execution time.
"""
import asyncio
import functools
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from opik import track

from app.core.database import get_db_context
from app.models.trace import Trace

logger = logging.getLogger(__name__)


def track_tool(tool_name: str):
    """
    Decorator that automatically traces tool executions with Opik.
    
    This decorator:
    1. Applies Opik's @track decorator for cloud tracing
    2. Persists trace data to the local database
    3. Captures tool metadata: name, inputs, outputs, duration, errors
    4. Links tool traces to parent agent sessions via session_id
    
    Usage:
        @track_tool("read_file")
        async def read_file_impl(path: str, context: AgentContext, **kwargs):
            # Tool implementation
            return result
    
    Args:
        tool_name: Name of the tool being traced (e.g., 'read_file', 'write_file')
    
    Returns:
        Decorated function with automatic tracing
    """
    def decorator(func: Callable) -> Callable:
        # Apply Opik's cloud tracking
        opik_tracked_func = track(name=f"tool_{tool_name}")(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract context and metadata
            context = kwargs.get('context')
            user_id = context.user_id if context else None
            project_id = context.project_id if context else None
            session_id = context.session_id if context else None
            user_prompt = kwargs.get('user_prompt')  # Original user request
            
            # Generate trace ID
            trace_id = str(uuid4())
            start_time = datetime.utcnow()
            start_ms = time.time() * 1000
            
            # Prepare input data (truncate large inputs)
            input_data = {
                'tool': tool_name,
                'args': {},
            }
            
            # Capture tool-specific arguments (exclude context and internal params)
            for key, value in kwargs.items():
                if key not in ['context', 'user_prompt', 'parent_trace_id']:
                    str_value = str(value)
                    input_data['args'][key] = str_value[:1000] if len(str_value) > 1000 else str_value
            
            # Add positional args if any (usually tools don't use them, but just in case)
            if args:
                input_data['positional_args'] = [str(arg)[:1000] for arg in args]
            
            try:
                # Call the actual tool function (with Opik tracking)
                if asyncio.iscoroutinefunction(func):
                    result = await opik_tracked_func(*args, **kwargs)
                else:
                    result = opik_tracked_func(*args, **kwargs)
                
                # Calculate duration
                end_time = datetime.utcnow()
                duration_ms = int((time.time() * 1000) - start_ms)
                
                # Prepare output data
                output_data = {}
                if result is not None:
                    str_result = str(result)
                    output_data['result'] = str_result[:1000] if len(str_result) > 1000 else str_result
                    output_data['result_length'] = len(str_result)
                
                # Save trace to database
                if user_id:
                    await _save_tool_trace_to_db(
                        trace_id=trace_id,
                        user_id=user_id,
                        project_id=project_id,
                        session_id=session_id,
                        tool_name=tool_name,
                        user_prompt=user_prompt,
                        start_time=start_time,
                        end_time=end_time,
                        duration_ms=duration_ms,
                        input_data=input_data,
                        output_data=output_data,
                        status='success',
                    )
                
                return result
                
            except Exception as e:
                # Calculate duration even on error
                end_time = datetime.utcnow()
                duration_ms = int((time.time() * 1000) - start_ms)
                
                # Save failed trace
                if user_id:
                    await _save_tool_trace_to_db(
                        trace_id=trace_id,
                        user_id=user_id,
                        project_id=project_id,
                        session_id=session_id,
                        tool_name=tool_name,
                        user_prompt=user_prompt,
                        start_time=start_time,
                        end_time=end_time,
                        duration_ms=duration_ms,
                        input_data=input_data,
                        output_data={'error': str(e), 'error_type': type(e).__name__},
                        status='error',
                        error=str(e),
                    )
                
                # Re-raise the exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous tools, we'll wrap in an async context if needed
            # Most tools are sync, so this handles them
            context = kwargs.get('context')
            user_id = context.user_id if context else None
            
            # For sync functions, we'll skip DB persistence to avoid blocking
            # but still apply Opik cloud tracking
            logger.debug(f"Sync tool {tool_name} called (DB persistence skipped)")
            return opik_tracked_func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def _save_tool_trace_to_db(
    trace_id: str,
    user_id: int,
    tool_name: str,
    start_time: datetime,
    end_time: datetime,
    duration_ms: int,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    status: str,
    project_id: Optional[int] = None,
    session_id: Optional[str] = None,
    user_prompt: Optional[str] = None,
    error: Optional[str] = None,
):
    """Save tool trace to database with error handling."""
    try:
        async with get_db_context() as session:
            # Create metadata
            meta_data = {
                'status': status,
                'tool': tool_name,
            }
            if session_id:
                meta_data['session_id'] = session_id
            if user_prompt:
                meta_data['user_prompt'] = user_prompt[:500]  # Truncate long prompts
            if error:
                meta_data['error'] = error[:500]
            
            trace = Trace(
                id=trace_id,
                user_id=user_id,
                project_id=project_id,
                trace_type='tool_execution',
                name=f"{tool_name}",
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                input_data=input_data,
                output_data=output_data,
                meta_data=meta_data,
                tags=['tool', tool_name, status],
            )
            
            session.add(trace)
            await session.commit()
            
            logger.info(f"Saved tool trace {trace_id}: {tool_name} ({duration_ms}ms, {status})")
            
    except Exception as e:
        logger.error(f"Failed to save tool trace to database: {e}")
        # Don't fail the operation just because DB persistence failed
