"""Traefik dynamic routing service.

Generates Docker labels for Traefik reverse proxy routing.
Enables subdomain-based access to project containers.
"""
from dataclasses import dataclass
from typing import Dict, Optional

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraefikRoute:
    """Traefik routing configuration."""
    subdomain: str
    full_url: str
    service_port: int
    labels: Dict[str, str]


class TraefikService:
    """Traefik dynamic routing management.
    
    Generates Docker labels that Traefik uses for automatic
    subdomain-based routing to project containers.
    """
    
    # Base domain for local development
    BASE_DOMAIN = getattr(settings, 'codi_domain', 'codi.local')
    
    # Default ports for different frameworks
    FRAMEWORK_PORTS = {
        "flutter": 80,      # nginx serving static files
        "nextjs": 3000,     # Next.js standalone server
        "react": 80,        # nginx serving static files
        "react_native": 80, # nginx serving expo web build
    }
    
    def __init__(self, base_domain: Optional[str] = None) -> None:
        """Initialize Traefik service.
        
        Args:
            base_domain: Base domain for subdomains (default: codi.local)
        """
        self.base_domain = base_domain or self.BASE_DOMAIN
    
    def generate_labels(
        self,
        project_slug: str,
        container_name: str,
        port: int = 80,
        is_preview: bool = False,
        branch: Optional[str] = None,
        enable_tls: bool = False,
    ) -> Dict[str, str]:
        """Generate Traefik Docker labels for routing.
        
        Args:
            project_slug: URL-safe project identifier
            container_name: Docker container name
            port: Container port to route to
            is_preview: Whether this is a preview deployment
            branch: Branch name for preview deployments
            enable_tls: Enable HTTPS (requires TLS setup)
            
        Returns:
            Dictionary of Docker labels for Traefik
        """
        # Generate subdomain
        if is_preview and branch:
            # Preview format: project-slug-preview-branch.codi.local
            safe_branch = self._sanitize_subdomain(branch)
            subdomain = f"{project_slug}-preview-{safe_branch}"
        else:
            # Main format: project-slug.codi.local
            subdomain = project_slug
        
        router_name = container_name.replace("-", "_")
        host = f"{subdomain}.{self.base_domain}"
        
        labels = {
            # Enable Traefik
            "traefik.enable": "true",
            
            # HTTP Router
            f"traefik.http.routers.{router_name}.rule": f"Host(`{host}`)",
            f"traefik.http.routers.{router_name}.entrypoints": "web",
            
            # Service port
            f"traefik.http.services.{router_name}.loadbalancer.server.port": str(port),
            
            # Codi metadata
            "codi.project.slug": project_slug,
            "codi.deployment.preview": str(is_preview).lower(),
        }
        
        if branch:
            labels["codi.deployment.branch"] = branch
        
        if enable_tls:
            # HTTPS Router
            labels[f"traefik.http.routers.{router_name}-secure.rule"] = f"Host(`{host}`)"
            labels[f"traefik.http.routers.{router_name}-secure.entrypoints"] = "websecure"
            labels[f"traefik.http.routers.{router_name}-secure.tls"] = "true"
        
        logger.debug(f"Generated Traefik labels for {host}: {labels}")
        return labels
    
    def _sanitize_subdomain(self, value: str) -> str:
        """Sanitize a string for use in subdomain.
        
        Args:
            value: String to sanitize
            
        Returns:
            URL-safe subdomain part
        """
        import re
        # Replace slashes with hyphens (for branch names like feature/foo)
        sanitized = value.replace("/", "-").replace("_", "-")
        # Remove invalid characters
        sanitized = re.sub(r'[^a-z0-9-]', '', sanitized.lower())
        # Remove consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Trim hyphens from ends
        return sanitized.strip('-')[:30]  # Max 30 chars
    
    def get_subdomain_url(
        self,
        project_slug: str,
        is_preview: bool = False,
        branch: Optional[str] = None,
        use_https: bool = False,
    ) -> str:
        """Get the full URL for a project subdomain.
        
        Args:
            project_slug: URL-safe project identifier
            is_preview: Whether this is a preview deployment  
            branch: Branch name for preview deployments
            use_https: Use HTTPS scheme
            
        Returns:
            Full URL (e.g., https://my-project.codi.local)
        """
        if is_preview and branch:
            safe_branch = self._sanitize_subdomain(branch)
            subdomain = f"{project_slug}-preview-{safe_branch}"
        else:
            subdomain = project_slug
        
        scheme = "https" if use_https else "http"
        return f"{scheme}://{subdomain}.{self.base_domain}"
    
    def get_preview_url(self, project_slug: str, branch: str, use_https: bool = False) -> str:
        """Convenience method for preview URL.
        
        Args:
            project_slug: URL-safe project identifier
            branch: Branch name
            use_https: Use HTTPS scheme
            
        Returns:
            Preview URL
        """
        return self.get_subdomain_url(project_slug, is_preview=True, branch=branch, use_https=use_https)
    
    def get_port_for_framework(self, framework: str) -> int:
        """Get the default port for a framework.
        
        Args:
            framework: Framework name
            
        Returns:
            Port number
        """
        return self.FRAMEWORK_PORTS.get(framework.lower(), 80)
    
    def parse_route_from_labels(self, labels: Dict[str, str]) -> Optional[TraefikRoute]:
        """Parse routing info from container labels.
        
        Args:
            labels: Container Docker labels
            
        Returns:
            TraefikRoute or None if not a Codi container
        """
        if "codi.project.slug" not in labels:
            return None
        
        project_slug = labels["codi.project.slug"]
        is_preview = labels.get("codi.deployment.preview", "false") == "true"
        branch = labels.get("codi.deployment.branch")
        
        # Find port from labels
        port = 80
        for key, value in labels.items():
            if "loadbalancer.server.port" in key:
                port = int(value)
                break
        
        url = self.get_subdomain_url(project_slug, is_preview, branch)
        
        return TraefikRoute(
            subdomain=f"{project_slug}.{self.base_domain}",
            full_url=url,
            service_port=port,
            labels=labels,
        )


# Singleton instance
_traefik_service: Optional[TraefikService] = None


def get_traefik_service() -> TraefikService:
    """Get or create TraefikService singleton."""
    global _traefik_service
    if _traefik_service is None:
        _traefik_service = TraefikService()
    return _traefik_service
