"""Services package."""
# Domain services
from app.services.domain import (
    EncryptionService,
    StarterTemplateService,
    DeploymentService,
    FrameworkDetector,
    detect_framework,
)

# Infrastructure services
from app.services.infrastructure import (
    LocalGitService,
    get_git_service,
    DockerService,
    get_docker_service,
    TraefikService,
    get_traefik_service,
)

__all__ = [
    # Domain
    "EncryptionService",
    "StarterTemplateService",
    "DeploymentService",
    "FrameworkDetector",
    "detect_framework",
    # Infrastructure
    "LocalGitService",
    "get_git_service",
    "DockerService",
    "get_docker_service",
    "TraefikService",
    "get_traefik_service",
]
