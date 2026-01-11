"""Celery application configuration and task definitions."""
import asyncio
from datetime import datetime
from typing import Any, Dict

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "codi_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=86400,  # Results expire after 24 hours
)


# Worker-level database initialization (once per worker, not per task)
_worker_db_initialized = False


@worker_process_init.connect
def init_worker_db(**kwargs):
    """Initialize database connections when a worker process starts.
    
    This runs once per forked worker process, creating fresh
    database connections that work with the worker's event loop.
    """
    global _worker_db_initialized
    
    if _worker_db_initialized:
        return
    
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    import app.database as db_module
    
    logger.info("Initializing database connections for worker process")
    
    # Create a new engine for this worker process
    db_module.engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    
    # Create a new session factory
    db_module.async_session_factory = async_sessionmaker(
        db_module.engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    _worker_db_initialized = True
    logger.info("Worker database connections initialized")


@worker_process_shutdown.connect
def shutdown_worker_db(**kwargs):
    """Clean up database connections when worker shuts down."""
    global _worker_db_initialized
    
    if not _worker_db_initialized:
        return
    
    import app.database as db_module
    
    logger.info("Closing worker database connections")
    
    # Close the engine pool synchronously
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(db_module.engine.dispose())
    except Exception as e:
        logger.warning(f"Error disposing engine: {e}")
    finally:
        loop.close()
    
    _worker_db_initialized = False


def run_async(coro: Any) -> Any:
    """Run an async coroutine in Celery task context.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coro)
    finally:
        # Clean up pending tasks before closing
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()


@celery_app.task(bind=True, name="tasks.run_agent_workflow")
def run_agent_workflow_task(
    self: Any,
    task_id: str,
    project_id: int,
    user_id: int,
    user_message: str,
    github_token_encrypted: str,
) -> Dict[str, Any]:
    """Celery task to run the agent workflow.

    Args:
        self: Celery task instance
        task_id: Unique task identifier
        project_id: Project ID
        user_id: User ID
        user_message: User's message/command
        github_token_encrypted: Encrypted GitHub access token

    Returns:
        Dictionary with task results
    """
    from app.services.encryption import encryption_service
    from app.workflows.executor import WorkflowExecutor

    logger.info(
        f"Starting agent workflow task",
        task_id=task_id,
        project_id=project_id,
        user_id=user_id,
    )

    start_time = datetime.utcnow()

    try:
        # Decrypt GitHub token
        github_token = encryption_service.decrypt_token(github_token_encrypted)

        # Create workflow executor
        executor = WorkflowExecutor(
            project_id=project_id,
            user_id=user_id,
            github_token=github_token,
            task_id=task_id,
        )

        # Run the workflow (this is async, so we need to run it in the event loop)
        result = run_async(executor.execute(user_message))

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.info(
            f"Agent workflow completed",
            task_id=task_id,
            duration_seconds=duration,
            success=True,
        )

        return {
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "duration_seconds": duration,
        }

    except Exception as e:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        logger.error(
            f"Agent workflow failed",
            task_id=task_id,
            error=str(e),
            duration_seconds=duration,
        )

        # Update task state to failure
        self.update_state(
            state="FAILURE",
            meta={
                "task_id": task_id,
                "error": str(e),
                "duration_seconds": duration,
            },
        )

        raise


@celery_app.task(bind=True, name="tasks.trigger_build")
def trigger_build_task(
    self: Any,
    project_id: int,
    repo_full_name: str,
    github_token_encrypted: str,
    branch: str = "main",
) -> Dict[str, Any]:
    """Celery task to trigger a GitHub Actions build.

    Args:
        self: Celery task instance
        project_id: Project ID
        repo_full_name: Full repository name (owner/repo)
        github_token_encrypted: Encrypted GitHub access token
        branch: Branch to build

    Returns:
        Dictionary with build trigger results
    """
    from app.services.encryption import encryption_service
    from app.services.github import GitHubService

    logger.info(
        f"Triggering build for {repo_full_name}",
        project_id=project_id,
        branch=branch,
    )

    try:
        # Decrypt GitHub token
        github_token = encryption_service.decrypt_token(github_token_encrypted)

        # Create GitHub service
        github_service = GitHubService(access_token=github_token)

        # Trigger workflow
        result = github_service.trigger_workflow(
            repo_full_name=repo_full_name,
            workflow_file="flutter_web_build.yml",
            ref=branch,
        )

        logger.info(
            f"Build triggered successfully",
            project_id=project_id,
            workflow_id=result.get("workflow_id"),
        )

        return {
            "status": "triggered",
            "project_id": project_id,
            "repo_full_name": repo_full_name,
            "branch": branch,
            "workflow": result,
        }

    except Exception as e:
        logger.error(
            f"Failed to trigger build",
            project_id=project_id,
            error=str(e),
        )
        raise


@celery_app.task(bind=True, name="tasks.poll_build_status")
def poll_build_status_task(
    self: Any,
    project_id: int,
    repo_full_name: str,
    run_id: int,
    github_token_encrypted: str,
) -> Dict[str, Any]:
    """Celery task to poll build status.

    Args:
        self: Celery task instance
        project_id: Project ID
        repo_full_name: Full repository name (owner/repo)
        run_id: Workflow run ID
        github_token_encrypted: Encrypted GitHub access token

    Returns:
        Dictionary with build status
    """
    from app.services.encryption import encryption_service
    from app.services.github import GitHubService

    try:
        # Decrypt GitHub token
        github_token = encryption_service.decrypt_token(github_token_encrypted)

        # Create GitHub service
        github_service = GitHubService(access_token=github_token)

        # Get run status
        status = github_service.get_workflow_run_status(
            repo_full_name=repo_full_name,
            run_id=run_id,
        )

        return {
            "project_id": project_id,
            "run_id": run_id,
            "status": status,
        }

    except Exception as e:
        logger.error(
            f"Failed to poll build status",
            project_id=project_id,
            run_id=run_id,
            error=str(e),
        )
        raise


@celery_app.task(name="tasks.cleanup_old_logs")
def cleanup_old_logs_task(days_to_keep: int = 30) -> Dict[str, Any]:
    """Celery task to clean up old operation logs.

    Args:
        days_to_keep: Number of days to keep logs

    Returns:
        Dictionary with cleanup results
    """
    from datetime import timedelta

    from sqlalchemy import delete

    from app.database import get_db_context
    from app.models.operation_log import OperationLog

    async def do_cleanup() -> int:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        async with get_db_context() as session:
            result = await session.execute(
                delete(OperationLog).where(OperationLog.created_at < cutoff_date)
            )
            return result.rowcount or 0

    deleted_count = run_async(do_cleanup())

    logger.info(
        f"Cleaned up old logs",
        days_to_keep=days_to_keep,
        deleted_count=deleted_count,
    )

    return {
        "status": "completed",
        "deleted_count": deleted_count,
        "days_to_keep": days_to_keep,
    }


# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "cleanup-old-logs-daily": {
        "task": "tasks.cleanup_old_logs",
        "schedule": 86400.0,  # Run daily
        "args": (30,),  # Keep 30 days
    },
}
