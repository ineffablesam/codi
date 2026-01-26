"""API package for FastAPI routes."""
from app.api.v1 import (
    auth_router,
    projects_router,
    agents_router,
    health_router,
    files_router,
    backend_router,
    containers_router,
    deployments_router,
    plans_router,
    chats_router,
)

__all__ = [
    "auth_router",
    "projects_router",
    "agents_router",
    "health_router",
    "files_router",
    "backend_router",
    "containers_router",
    "deployments_router",
    "plans_router",
    "chats_router",
]
