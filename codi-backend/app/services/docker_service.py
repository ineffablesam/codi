"""Docker container lifecycle management service.

Provides Docker container operations for project builds and deployments.
Uses docker-py for container management.
"""
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import docker
from docker.errors import DockerException, ImageNotFound, NotFound, APIError
from docker.models.containers import Container
from docker.models.images import Image

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ContainerStatus(str, Enum):
    """Container status enum."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    EXITED = "exited"
    ERROR = "error"


@dataclass
class ContainerInfo:
    """Container information dataclass."""
    id: str
    short_id: str
    name: str
    status: ContainerStatus
    image: str
    created_at: datetime
    ports: Dict[str, Any]
    labels: Dict[str, str]
    
    @property
    def is_running(self) -> bool:
        return self.status == ContainerStatus.RUNNING


@dataclass
class ContainerStats:
    """Container resource statistics."""
    container_id: str
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx_bytes: int
    network_tx_bytes: int
    timestamp: datetime


@dataclass 
class BuildResult:
    """Docker image build result."""
    image_id: str
    image_tag: str
    build_logs: List[str]
    success: bool
    error: Optional[str] = None


class DockerService:
    """Docker container lifecycle management.
    
    Handles building images, creating containers, starting/stopping,
    log retrieval, and resource monitoring.
    """
    
    # Base path for project repositories
    REPOS_BASE = "/var/codi/repos"
    
    # Default resource limits
    DEFAULT_CPU_LIMIT = 0.5  # 50% of one CPU
    DEFAULT_MEMORY_LIMIT = "512m"
    DEFAULT_MEMORY_SWAP = "1g"
    
    # Traefik network name
    TRAEFIK_NETWORK = "codi-network"
    
    def __init__(self) -> None:
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
            self._verify_connection()
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise RuntimeError(f"Docker not available: {e}")
    
    def _verify_connection(self) -> None:
        """Verify Docker daemon connection."""
        try:
            self.client.ping()
            logger.info("Docker daemon connection verified")
        except Exception as e:
            logger.error(f"Docker daemon not responding: {e}")
            raise RuntimeError("Docker daemon not responding")
    
    def _get_dockerfile_for_framework(self, framework: str) -> str:
        """Get Dockerfile content for a framework.
        
        Args:
            framework: Framework type (flutter, nextjs, react, etc.)
            
        Returns:
            Dockerfile content as string
        """
        dockerfiles = {
            "flutter": '''FROM ghcr.io/cirruslabs/flutter:stable AS builder
WORKDIR /app
COPY pubspec.* ./
RUN flutter pub get
COPY . .
RUN flutter build web --release

FROM nginx:alpine
COPY --from=builder /app/build/web /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf 2>/dev/null || true
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
''',
            "nextjs": '''FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
''',
            "react": '''FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
''',
            "react_native": '''FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx expo export -p web

FROM nginx:alpine  
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
''',
        }
        return dockerfiles.get(framework, dockerfiles["react"])
    
    async def build_image(
        self,
        project_path: str,
        image_tag: str,
        framework: str = "auto",
        dockerfile_path: Optional[str] = None,
        build_args: Optional[Dict[str, str]] = None,
    ) -> BuildResult:
        """Build a Docker image from project source.
        
        Args:
            project_path: Path to project source code
            image_tag: Tag for the built image (e.g., codi/project-slug:latest)
            framework: Framework type for Dockerfile selection
            dockerfile_path: Optional custom Dockerfile path
            build_args: Optional build arguments
            
        Returns:
            BuildResult with image info and logs
        """
        logger.info(f"Building image {image_tag} from {project_path}")
        
        build_logs: List[str] = []
        dockerfile_content = None
        
        try:
            # Check if Dockerfile exists, otherwise create one
            dockerfile_in_project = os.path.join(project_path, "Dockerfile")
            if not os.path.exists(dockerfile_in_project) and not dockerfile_path:
                # Auto-detect framework if needed
                if framework == "auto":
                    framework = self._detect_framework(project_path)
                
                dockerfile_content = self._get_dockerfile_for_framework(framework)
                
                # Write temporary Dockerfile
                with open(dockerfile_in_project, "w") as f:
                    f.write(dockerfile_content)
                build_logs.append(f"Created Dockerfile for {framework} framework")
            
            # Build the image
            loop = asyncio.get_event_loop()
            image, logs = await loop.run_in_executor(
                None,
                lambda: self.client.images.build(
                    path=project_path,
                    tag=image_tag,
                    dockerfile=dockerfile_path or "Dockerfile",
                    buildargs=build_args or {},
                    rm=True,  # Remove intermediate containers
                    forcerm=True,  # Force remove on failure
                )
            )
            
            # Collect build logs
            for log_entry in logs:
                if "stream" in log_entry:
                    log_line = log_entry["stream"].strip()
                    if log_line:
                        build_logs.append(log_line)
            
            logger.info(f"Successfully built image {image_tag}, id={image.short_id}")
            
            return BuildResult(
                image_id=image.id,
                image_tag=image_tag,
                build_logs=build_logs,
                success=True,
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to build image {image_tag}: {error_msg}")
            build_logs.append(f"ERROR: {error_msg}")
            
            return BuildResult(
                image_id="",
                image_tag=image_tag,
                build_logs=build_logs,
                success=False,
                error=error_msg,
            )
    
    def _detect_framework(self, project_path: str) -> str:
        """Auto-detect project framework from files.
        
        Args:
            project_path: Path to project
            
        Returns:
            Framework name
        """
        if os.path.exists(os.path.join(project_path, "pubspec.yaml")):
            return "flutter"
        elif os.path.exists(os.path.join(project_path, "next.config.js")) or \
             os.path.exists(os.path.join(project_path, "next.config.ts")) or \
             os.path.exists(os.path.join(project_path, "next.config.mjs")):
            return "nextjs"
        elif os.path.exists(os.path.join(project_path, "app.json")):
            # Expo/React Native
            return "react_native"
        elif os.path.exists(os.path.join(project_path, "package.json")):
            # Generic React/Vite
            return "react"
        return "react"  # Default fallback
    
    async def create_container(
        self,
        image: str,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, int]] = None,
        cpu_limit: float = DEFAULT_CPU_LIMIT,
        memory_limit: str = DEFAULT_MEMORY_LIMIT,
        network: str = TRAEFIK_NETWORK,
        auto_start: bool = True,
    ) -> ContainerInfo:
        """Create a new container.
        
        Args:
            image: Docker image name/tag
            name: Container name
            labels: Docker labels (including Traefik routing)
            environment: Environment variables
            ports: Port mappings {container_port: host_port}
            cpu_limit: CPU limit (0.5 = 50% of one CPU)
            memory_limit: Memory limit (e.g., "512m", "1g")
            network: Docker network to connect to
            auto_start: Start container immediately after creation
            
        Returns:
            ContainerInfo with container details
        """
        logger.info(f"Creating container {name} from image {image}")
        
        try:
            # Ensure network exists
            await self._ensure_network_exists(network)
            
            # Create container
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: self.client.containers.create(
                    image=image,
                    name=name,
                    labels=labels or {},
                    environment=environment or {},
                    ports=ports,
                    network=network,
                    cpu_period=100000,
                    cpu_quota=int(cpu_limit * 100000),
                    mem_limit=memory_limit,
                    memswap_limit=self.DEFAULT_MEMORY_SWAP,
                    detach=True,
                    restart_policy={"Name": "unless-stopped"},
                )
            )
            
            if auto_start:
                await loop.run_in_executor(None, container.start)
            
            # Refresh to get updated status
            container.reload()
            
            info = self._container_to_info(container)
            logger.info(f"Created container {name}, id={info.short_id}, status={info.status}")
            
            return info
            
        except ImageNotFound:
            logger.error(f"Image not found: {image}")
            raise ValueError(f"Image not found: {image}")
        except Exception as e:
            logger.error(f"Failed to create container {name}: {e}")
            raise
    
    async def _ensure_network_exists(self, network_name: str) -> None:
        """Ensure Docker network exists, create if not."""
        try:
            self.client.networks.get(network_name)
        except NotFound:
            logger.info(f"Creating Docker network: {network_name}")
            self.client.networks.create(network_name, driver="bridge")
    
    def _container_to_info(self, container: Container) -> ContainerInfo:
        """Convert Docker container to ContainerInfo."""
        status_map = {
            "created": ContainerStatus.CREATED,
            "running": ContainerStatus.RUNNING,
            "paused": ContainerStatus.PAUSED,
            "exited": ContainerStatus.EXITED,
            "dead": ContainerStatus.ERROR,
        }
        
        return ContainerInfo(
            id=container.id,
            short_id=container.short_id,
            name=container.name,
            status=status_map.get(container.status, ContainerStatus.ERROR),
            image=container.image.tags[0] if container.image.tags else container.image.short_id,
            created_at=datetime.fromisoformat(container.attrs["Created"].replace("Z", "+00:00")),
            ports=container.ports,
            labels=container.labels,
        )
    
    async def start_container(self, container_id: str) -> ContainerInfo:
        """Start a stopped container.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            Updated ContainerInfo
        """
        logger.info(f"Starting container {container_id}")
        
        try:
            loop = asyncio.get_event_loop()
            container = self.client.containers.get(container_id)
            await loop.run_in_executor(None, container.start)
            container.reload()
            
            info = self._container_to_info(container)
            logger.info(f"Started container {container_id}, status={info.status}")
            return info
            
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def stop_container(self, container_id: str, timeout: int = 10) -> ContainerInfo:
        """Stop a running container.
        
        Args:
            container_id: Container ID or name
            timeout: Seconds to wait before SIGKILL
            
        Returns:
            Updated ContainerInfo
        """
        logger.info(f"Stopping container {container_id}")
        
        try:
            loop = asyncio.get_event_loop()
            container = self.client.containers.get(container_id)
            await loop.run_in_executor(None, lambda: container.stop(timeout=timeout))
            container.reload()
            
            info = self._container_to_info(container)
            logger.info(f"Stopped container {container_id}, status={info.status}")
            return info
            
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def restart_container(self, container_id: str, timeout: int = 10) -> ContainerInfo:
        """Restart a container.
        
        Args:
            container_id: Container ID or name
            timeout: Seconds to wait for stop before SIGKILL
            
        Returns:
            Updated ContainerInfo
        """
        logger.info(f"Restarting container {container_id}")
        
        try:
            loop = asyncio.get_event_loop()
            container = self.client.containers.get(container_id)
            await loop.run_in_executor(None, lambda: container.restart(timeout=timeout))
            container.reload()
            
            info = self._container_to_info(container)
            logger.info(f"Restarted container {container_id}, status={info.status}")
            return info
            
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def remove_container(self, container_id: str, force: bool = True) -> bool:
        """Remove a container.
        
        Args:
            container_id: Container ID or name
            force: Force remove running container
            
        Returns:
            True if removed successfully
        """
        logger.info(f"Removing container {container_id}")
        
        try:
            loop = asyncio.get_event_loop()
            container = self.client.containers.get(container_id)
            await loop.run_in_executor(None, lambda: container.remove(force=force))
            
            logger.info(f"Removed container {container_id}")
            return True
            
        except NotFound:
            logger.warning(f"Container not found: {container_id}")
            return False
    
    async def get_container(self, container_id: str) -> Optional[ContainerInfo]:
        """Get container information.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            ContainerInfo or None if not found
        """
        try:
            container = self.client.containers.get(container_id)
            return self._container_to_info(container)
        except NotFound:
            return None
    
    async def list_containers(
        self,
        labels: Optional[Dict[str, str]] = None,
        all: bool = True,
    ) -> List[ContainerInfo]:
        """List containers, optionally filtered by labels.
        
        Args:
            labels: Filter by labels
            all: Include stopped containers
            
        Returns:
            List of ContainerInfo
        """
        filters = {}
        if labels:
            filters["label"] = [f"{k}={v}" for k, v in labels.items()]
        
        containers = self.client.containers.list(all=all, filters=filters)
        return [self._container_to_info(c) for c in containers]
    
    async def get_container_logs(
        self,
        container_id: str,
        tail: int = 100,
        since: Optional[datetime] = None,
        timestamps: bool = True,
    ) -> List[str]:
        """Get container logs.
        
        Args:
            container_id: Container ID or name
            tail: Number of lines from end
            since: Only logs since this time
            timestamps: Include timestamps
            
        Returns:
            List of log lines
        """
        try:
            container = self.client.containers.get(container_id)
            
            kwargs = {
                "tail": tail,
                "timestamps": timestamps,
                "stdout": True,
                "stderr": True,
            }
            if since:
                kwargs["since"] = since
            
            logs = container.logs(**kwargs)
            
            if isinstance(logs, bytes):
                return logs.decode("utf-8", errors="replace").split("\n")
            return list(logs)
            
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def stream_logs(
        self,
        container_id: str,
        since: Optional[datetime] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream container logs in real-time.
        
        Args:
            container_id: Container ID or name
            since: Only logs since this time
            
        Yields:
            Log lines as they arrive
        """
        try:
            container = self.client.containers.get(container_id)
            
            kwargs = {
                "stream": True,
                "follow": True,
                "timestamps": True,
                "stdout": True,
                "stderr": True,
            }
            if since:
                kwargs["since"] = since
            
            for chunk in container.logs(**kwargs):
                if isinstance(chunk, bytes):
                    yield chunk.decode("utf-8", errors="replace")
                else:
                    yield str(chunk)
                    
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def get_container_stats(self, container_id: str) -> ContainerStats:
        """Get container resource statistics.
        
        Args:
            container_id: Container ID or name
            
        Returns:
            ContainerStats with CPU/memory/network metrics
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            num_cpus = stats["cpu_stats"].get("online_cpus", 1)
            
            cpu_percent = 0.0
            if system_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
            
            # Memory stats
            memory_usage = stats["memory_stats"].get("usage", 0)
            memory_limit = stats["memory_stats"].get("limit", 1)
            memory_usage_mb = memory_usage / (1024 * 1024)
            memory_limit_mb = memory_limit / (1024 * 1024)
            memory_percent = (memory_usage / memory_limit) * 100.0 if memory_limit > 0 else 0.0
            
            # Network stats
            networks = stats.get("networks", {})
            rx_bytes = sum(n.get("rx_bytes", 0) for n in networks.values())
            tx_bytes = sum(n.get("tx_bytes", 0) for n in networks.values())
            
            return ContainerStats(
                container_id=container_id,
                cpu_percent=round(cpu_percent, 2),
                memory_usage_mb=round(memory_usage_mb, 2),
                memory_limit_mb=round(memory_limit_mb, 2),
                memory_percent=round(memory_percent, 2),
                network_rx_bytes=rx_bytes,
                network_tx_bytes=tx_bytes,
                timestamp=datetime.utcnow(),
            )
            
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def update_container_labels(
        self,
        container_id: str,
        labels: Dict[str, str],
    ) -> ContainerInfo:
        """Update container labels (requires container recreation).
        
        Note: Docker doesn't support updating labels directly.
        This creates a new container with updated labels.
        
        Args:
            container_id: Container ID or name
            labels: New labels to set
            
        Returns:
            New ContainerInfo
        """
        try:
            old_container = self.client.containers.get(container_id)
            old_config = old_container.attrs
            
            # Stop and remove old container
            old_name = old_container.name
            old_image = old_container.image.tags[0] if old_container.image.tags else old_container.image.id
            
            # Merge old labels with new ones
            new_labels = {**old_container.labels, **labels}
            
            await self.stop_container(container_id)
            await self.remove_container(container_id)
            
            # Create new container with same config but updated labels
            return await self.create_container(
                image=old_image,
                name=old_name,
                labels=new_labels,
                environment=old_config["Config"].get("Env"),
            )
            
        except NotFound:
            raise ValueError(f"Container not found: {container_id}")
    
    async def cleanup_unused_images(self, project_prefix: str = "codi/") -> int:
        """Remove unused Docker images for Codi projects.
        
        Args:
            project_prefix: Image name prefix to filter
            
        Returns:
            Number of images removed
        """
        try:
            images = self.client.images.list(filters={"dangling": True})
            removed = 0
            
            for image in images:
                for tag in image.tags:
                    if tag.startswith(project_prefix):
                        try:
                            self.client.images.remove(image.id, force=True)
                            removed += 1
                            logger.info(f"Removed unused image: {tag}")
                        except Exception as e:
                            logger.warning(f"Failed to remove image {tag}: {e}")
            
            return removed
            
        except Exception as e:
            logger.error(f"Failed to cleanup images: {e}")
            return 0


# Singleton instance
_docker_service: Optional[DockerService] = None


def get_docker_service() -> DockerService:
    """Get or create DockerService singleton."""
    global _docker_service
    if _docker_service is None:
        _docker_service = DockerService()
    return _docker_service
