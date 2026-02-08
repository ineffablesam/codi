"""API package initialization."""
from app.api.v1 import (
    agents_router,
    auth_router,
    backend_router,
    chats_router,
    containers_router,
    deployments_router,
    environment_router,
    files_router,
    health_router,
    opik_router,
    opik_extensions_router,
    plans_router,
    projects_router,
)

__all__ = [
    "agents_router",
    "auth_router",
    "backend_router",
    "chats_router",
    "containers_router",
    "deployments_router",
    "environment_router",
    "files_router",
    "health_router",
    "opik_router",
    "opik_extensions_router",
    "plans_router",
    "projects_router",
]
