"""API v1 routes package."""
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.agents import router as agents_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.files import router as files_router
from app.api.v1.routes.backend_oauth import router as backend_router
from app.api.v1.routes.containers import router as containers_router
from app.api.v1.routes.deployments import router as deployments_router
from app.api.v1.routes.plans import router as plans_router
from app.api.v1.routes.chats import router as chats_router
from app.api.v1.routes.environment import router as environment_router
from app.api.v1.endpoints.opik import router as opik_router
from app.api.v1.endpoints.opik_extensions import router as opik_extensions_router

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
    "environment_router",
    "opik_router",
    "opik_extensions_router",
]

