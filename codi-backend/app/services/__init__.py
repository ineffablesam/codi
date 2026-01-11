"""Services package."""
from app.services.encryption import EncryptionService
from app.services.git_service import LocalGitService, get_git_service
from app.services.starter_template import StarterTemplateService
from app.services.deployment import DeploymentService
from app.services.docker_service import DockerService, get_docker_service
from app.services.traefik_service import TraefikService, get_traefik_service
from app.services.framework_detector import FrameworkDetector, detect_framework

__all__ = [
    "EncryptionService",
    "LocalGitService",
    "get_git_service",
    "StarterTemplateService",
    "DeploymentService",
    "DockerService",
    "get_docker_service",
    "TraefikService",
    "get_traefik_service",
    "FrameworkDetector",
    "detect_framework",
]
