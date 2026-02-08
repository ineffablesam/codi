"""Custom decorator for persisting Opik traces to local database."""
import functools
import inspect
import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import uuid4

from opik import track
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.models.trace import Trace

logger = logging.getLogger(__name__)


def track_and_persist(
    project_name: Optional[str] = None,
    trace_type: str = "general",
):
    """
    Decorator that combines Opik cloud tracing with local database persistence.
    
    Usage:
        @track_and_persist(project_name="my-project", trace_type="summarization")
        async def my_function(user_id: int, project_id: Optional[int] = None, ...):
            # Function implementation
            return result
    
    Args:
        project_name: Opik project name for cloud tracing
        trace_type: Type of trace (e.g., 'summarization', 'code_generation')
    
    Notes:
        - Function must accept `user_id` parameter
        - Optionally accepts `project_id` parameter for project-level filtering
        - Automatically measures execution time
        - Saves trace to database if user_id is provided
    """
    def decorator(func: Callable) -> Callable:
        # Apply Opik's cloud tracking first
        opik_tracked_func = track(project_name=project_name)(func)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract user_id and project_id from kwargs
            user_id = kwargs.get('user_id')
            project_id = kwargs.get('project_id')
            
            if not user_id:
                # If no user_id, just use Opik tracking without DB persistence
                logger.debug("No user_id provided, skipping database persistence")
                return await opik_tracked_func(*args, **kwargs)
            
            # Generate trace ID
            trace_id = str(uuid4())
            start_time = datetime.utcnow()
            start_ms = time.time() * 1000
            
            # Prepare input data (truncate large inputs)
            input_data = {}
            for key, value in kwargs.items():
                if key not in ['user_id', 'project_id', 'db', 'session']:
                    str_value = str(value)
                    input_data[key] = str_value[:1000] if len(str_value) > 1000 else str_value
            
            try:
                # Call the actual function (with Opik tracking)
                result = await opik_tracked_func(*args, **kwargs)
                
                # Calculate duration
                end_time = datetime.utcnow()
                duration_ms = int((time.time() * 1000) - start_ms)
                
                # Prepare output data
                output_data = {}
                if result is not None:
                    str_result = str(result)
                    output_data['result'] = str_result[:1000] if len(str_result) > 1000 else str_result
                
                # Save trace to database
                await _save_trace_to_db(
                    trace_id=trace_id,
                    user_id=user_id,
                    project_id=project_id,
                    trace_type=trace_type,
                    name=f"{func.__name__}",
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    input_data=input_data,
                    output_data=output_data,
                    tags=[trace_type, func.__name__],
                    status='success',
                )
                
                return result
                
            except Exception as e:
                # Calculate duration even on error
                end_time = datetime.utcnow()
                duration_ms = int((time.time() * 1000) - start_ms)
                
                # Save failed trace
                await _save_trace_to_db(
                    trace_id=trace_id,
                    user_id=user_id,
                    project_id=project_id,
                    trace_type=trace_type,
                    name=f"{func.__name__}",
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    input_data=input_data,
                    output_data={'error': str(e)},
                    tags=[trace_type, func.__name__, 'error'],
                    status='error',
                )
                
                # Re-raise the exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions (future-proofing)
            logger.warning(f"Synchronous function {func.__name__} called with track_and_persist - consider using async")
            return opik_tracked_func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


async def _save_trace_to_db(
    trace_id: str,
    user_id: int,
    trace_type: str,
    name: str,
    start_time: datetime,
    end_time: datetime,
    duration_ms: int,
    input_data: dict,
    output_data: dict,
    tags: list,
    status: str,
    project_id: Optional[int] = None,
):
    """Save trace to database with error handling."""
    try:
        async with get_db_context() as session:
            trace = Trace(
                id=trace_id,
                user_id=user_id,
                project_id=project_id,
                trace_type=trace_type,
                name=name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                input_data=input_data,
                output_data=output_data,
                meta_data={'status': status},
                tags=tags,
            )
            
            session.add(trace)
            await session.commit()
            
            logger.info(f"Saved trace {trace_id} to database: {name} ({duration_ms}ms)")
            
    except Exception as e:
        logger.error(f"Failed to save trace to database: {e}")
        # Don't fail the operation just because DB persistence failed
