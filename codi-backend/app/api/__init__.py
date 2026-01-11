"""API package for FastAPI routes."""
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.agents import router as agents_router
from app.api.health import router as health_router
from app.api.files import router as files_router
from app.api.backend_oauth import router as backend_router
from app.api.containers import router as containers_router
from app.api.deployments import router as deployments_router

__all__ = [
    "auth_router",
    "projects_router",
    "agents_router",
    "health_router",
    "files_router",
    "backend_router",
    "containers_router",
    "deployments_router",
]
