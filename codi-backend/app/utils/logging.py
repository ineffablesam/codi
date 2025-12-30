"""Structured logging configuration using structlog."""
import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    # Determine log level based on environment
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Define shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_production:
        # Production: JSON output for log aggregation
        shared_processors.extend([
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])
    else:
        # Development: Pretty console output
        shared_processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding temporary context to logs."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize log context with key-value pairs."""
        self.context = kwargs

    def __enter__(self) -> "LogContext":
        """Enter context and bind variables."""
        structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and unbind variables."""
        structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_agent_activity(
    agent_name: str,
    activity: str,
    project_id: int,
    user_id: int,
    details: Dict[str, Any] | None = None,
) -> None:
    """Log agent activity with consistent structure.

    Args:
        agent_name: Name of the agent performing the activity
        activity: Description of the activity
        project_id: ID of the project being worked on
        user_id: ID of the user who initiated the task
        details: Optional additional details
    """
    logger = get_logger("agent")
    logger.info(
        activity,
        agent=agent_name,
        project_id=project_id,
        user_id=user_id,
        **(details or {}),
    )
