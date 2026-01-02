"""Main FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import agents_router, auth_router, health_router, projects_router, files_router, backend_router
from app.config import settings
from app.database import init_db
from app.utils.logging import get_logger, setup_logging

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("Starting Codi Backend API", version="1.0.0")

    # Initialize database tables (for development)
    if settings.debug:
        await init_db()
        logger.info("Database initialized")
    
    # Start Redis subscriber for cross-process WebSocket messaging
    # This receives messages from Celery workers and broadcasts to WebSocket connections
    try:
        from app.websocket.redis_broadcaster import redis_broadcaster
        from app.websocket.connection_manager import connection_manager
        
        async def on_redis_message(project_id: int, message: dict):
            """Callback when a message is received from Redis.
            
            Broadcasts the message to all local WebSocket connections for the project.
            """
            await connection_manager.send_to_local_connections(project_id, message)
        
        await redis_broadcaster.start_subscriber(on_redis_message)
        logger.info("Redis subscriber started for WebSocket messaging")
    except Exception as e:
        logger.error(f"Failed to start Redis subscriber: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Codi Backend API")
    
    # Clean up Redis broadcaster
    try:
        from app.websocket.redis_broadcaster import redis_broadcaster
        await redis_broadcaster.disconnect()
        logger.info("Redis broadcaster disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting Redis broadcaster: {e}")


# Create FastAPI application
app = FastAPI(
    title="Codi Backend API",
    description="AI-powered Flutter development platform API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    Args:
        request: HTTP request
        exc: Exception that occurred

    Returns:
        JSON error response
    """
    logger.error(
        f"Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )

    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
# files_router MUST come before projects_router since projects has catch-all /files/{path:path}
app.include_router(files_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(backend_router, prefix="/api/v1")

# Webhook router (no auth required - uses signature verification)
from app.api.webhooks import router as webhooks_router
app.include_router(webhooks_router, prefix="/api/v1")



@app.get("/")
async def root() -> dict:
    """Root endpoint with API information.

    Returns:
        API information
    """
    return {
        "name": "Codi Backend API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else None,
        "health": "/health",
    }


# Development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
