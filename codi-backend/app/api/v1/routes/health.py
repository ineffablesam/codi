"""Health check endpoints."""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter
from redis import asyncio as aioredis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint.

    Returns:
        Health status with timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check with dependency status.

    Returns:
        Status of all dependencies
    """
    status = {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {},
    }

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["dependencies"]["database"] = "connected"
    except Exception as e:
        status["dependencies"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"

    # Check Redis
    try:
        redis = aioredis.from_url(settings.redis_url)
        await redis.ping()
        await redis.close()
        status["dependencies"]["redis"] = "connected"
    except Exception as e:
        status["dependencies"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"

    return status


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Kubernetes liveness probe endpoint.

    Returns:
        Simple alive status
    """
    return {"status": "alive"}
