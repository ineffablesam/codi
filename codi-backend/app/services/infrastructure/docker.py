"""Docker container lifecycle management service.

Provides Docker container operations for project builds and deployments.
Uses docker-py for container management.
"""
import asyncio
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

import docker
from docker.errors import DockerException, ImageNotFound, NotFound, APIError, BuildError
from docker.models.containers import Container
from docker.models.images import Image

from app.core.config import settings
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
            self._verify_buildx()
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
    
    def _verify_buildx(self) -> None:
        """Verify Docker buildx is available."""
        try:
            result = subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Docker buildx available: {result.stdout.strip()}")
            else:
                logger.warning("Docker buildx not available, falling back to regular build")
        except Exception as e:
            logger.warning(f"Could not verify buildx: {e}")
    
    def _get_dockerfile_for_framework(self, framework: str, project_path: Optional[str] = None) -> str:
        """Get the default Dockerfile content for a given framework.
        
        Uses "Turbo" detection to bypass full builds if artifacts already exist on host.
        """
        # Turbo check logic - if artifacts exist on host, we can do a lightning fast copy-only build.
        # This is safe because both api and runner are Debian-based (glibc).
        is_turbo = False
        if project_path:
            if framework == "nextjs" and os.path.exists(os.path.join(project_path, ".next", "standalone")):
                is_turbo = True
            elif framework == "react" and os.path.exists(os.path.join(project_path, "dist", "index.html")):
                is_turbo = True
            elif framework == "flutter" and os.path.exists(os.path.join(project_path, "build", "web", "index.html")):
                is_turbo = True

        if is_turbo:
            logger.info(f"Turbo boost enabled: reusing host-built artifacts for {framework}")
            if framework == "nextjs":
                return '''FROM node:20-slim
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
# Copy standalone build and static files from host
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public
EXPOSE 3000
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=3 CMD curl -f http://localhost:3000/ || exit 1
CMD ["node", "server.js"]
'''
            else: # react, flutter
                dist_dir = "build/web" if framework == "flutter" else "dist"
                return f'''FROM nginx:stable
COPY {dist_dir} /usr/share/nginx/html
EXPOSE 80
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD curl -f http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
'''

        # Standard Multi-stage Fallback (Switch to Debian images for compatibility and speed)
        dockerfiles = {
            "flutter": '''FROM ghcr.io/cirruslabs/flutter:stable AS builder
WORKDIR /app
COPY pubspec.* ./
RUN flutter pub get
COPY . .
RUN flutter build web --release

FROM nginx:stable
COPY --from=builder /app/build/web /usr/share/nginx/html
EXPOSE 80
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD curl -f http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
''',
            "nextjs": '''FROM node:20-slim AS builder
WORKDIR /app
# Use cache mount for npm
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit
COPY . .
ENV NODE_OPTIONS="--max-old-space-size=2048"
ENV NEXT_CPU_COUNT=1
# Use cache mount for Next.js build cache
RUN --mount=type=cache,target=/app/.next/cache \
    npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 CMD curl -f http://localhost:3000/ || exit 1
CMD ["node", "server.js"]
''',
            "react": '''FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --no-audit
COPY . .
RUN npm run build

FROM nginx:stable
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD curl -f http://localhost/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
''',
            "react_native": '''FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit
COPY . .
RUN npx expo export -p web

FROM nginx:stable
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=3 CMD curl -f http://localhost/ || exit 1
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
        nocache: bool = False,
    ) -> BuildResult:
        """Build a Docker image from project source using buildx.
        
        Args:
            project_path: Path to project source code
            image_tag: Tag for the built image (e.g., codi/project-slug:latest)
            framework: Framework type for Dockerfile selection
            dockerfile_path: Optional custom Dockerfile path
            build_args: Optional build arguments
            nocache: Do not use cache when building the image
            
        Returns:
            BuildResult with image info and logs
        """
        logger.info(f"Building image {image_tag} from {project_path} (nocache={nocache})")
        
        build_logs: List[str] = []
        dockerfile_content = None
        
        try:
            # Ensure .dockerignore exists to prevent copying node_modules
            dockerignore_path = os.path.join(project_path, ".dockerignore")
            if not os.path.exists(dockerignore_path):
                dockerignore_content = """# Auto-generated by Codi
node_modules
.next
.git
*.log
.env*
.DS_Store
"""
                with open(dockerignore_path, "w") as f:
                    f.write(dockerignore_content)
                build_logs.append("Created .dockerignore to exclude node_modules")
            
            # Check if Dockerfile exists, otherwise create one in .codi/ to avoid cache invalidation
            codi_dir = os.path.join(project_path, ".codi")
            dockerfile_in_codi = os.path.join(codi_dir, "Dockerfile")
            dockerfile_in_project = os.path.join(project_path, "Dockerfile")
            
            # Use existing Dockerfile in project root, or create one in .codi/
            if os.path.exists(dockerfile_in_project):
                # User has their own Dockerfile, use it
                dockerfile_path = dockerfile_path or "Dockerfile"
            elif not dockerfile_path:
                # Auto-detect framework if needed
                if framework == "auto":
                    framework = self.detect_framework(project_path)
                
                dockerfile_content = self._get_dockerfile_for_framework(framework, project_path)
                
                # Write Dockerfile to .codi/ directory to prevent cache invalidation
                os.makedirs(codi_dir, exist_ok=True)
                with open(dockerfile_in_codi, "w") as f:
                    f.write(dockerfile_content)
                dockerfile_path = ".codi/Dockerfile"
                build_logs.append(f"Created .codi/Dockerfile for {framework} framework")
            
            # Compute build hashes for smart cache invalidation
            deps_hash, src_hash = self._compute_build_hashes(project_path)
            hash_labels = {
                "codi.deps_hash": deps_hash,
                "codi.src_hash": src_hash,
                "codi.built_at": datetime.utcnow().isoformat(),
            }
            
            # Build using docker build (standard) - less likely to crash dockerd than raw buildx in some envs
            cmd = [
                "docker", "build",
                "-t", image_tag,
                "-f", dockerfile_path or "Dockerfile",
            ]
            
            # Add no-cache flag if requested
            if nocache:
                cmd.append("--no-cache")
            
            # Add build arguments
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(["--build-arg", f"{key}={value}"])
            
            # Add labels for cache tracking
            for key, value in hash_labels.items():
                cmd.extend(["--label", f"{key}={value}"])
            
            # Add project path as build context
            cmd.append(project_path)
            
            logger.debug(f"Build command: {' '.join(cmd)}")
            
            # Enable BuildKit for cache mounts and faster builds
            env = os.environ.copy()
            env["DOCKER_BUILDKIT"] = "1"
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=project_path,
            )
            
            # Capture output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                log_line = line.decode('utf-8', errors='replace').strip()
                if log_line:
                    build_logs.append(log_line)
            
            await process.wait()
            
            if process.returncode != 0:
                # If build fails, allow one retry with --no-cache
                if not nocache:
                    logger.warning(f"Build failed (code {process.returncode}). Retrying with --no-cache...")
                    return await self.build_image(
                        project_path=project_path,
                        image_tag=image_tag,
                        framework=framework,
                        dockerfile_path=dockerfile_path,
                        build_args=build_args,
                        nocache=True,
                    )

                error_msg = f"Build failed with exit code {process.returncode}"
                logger.error(error_msg)
                return BuildResult(
                    image_id="",
                    image_tag=image_tag,
                    build_logs=build_logs,
                    success=False,
                    error=error_msg,
                )
            
            # Get the built image
            try:
                image = self.client.images.get(image_tag)
                logger.info(f"Successfully built image {image_tag}, id={image.short_id}")
                return BuildResult(
                    image_id=image.id,
                    image_tag=image_tag,
                    build_logs=build_logs,
                    success=True,
                )
            except ImageNotFound:
                error_msg = f"Image {image_tag} was built but not found"
                logger.error(error_msg)
                return BuildResult(
                    image_id="",
                    image_tag=image_tag,
                    build_logs=build_logs,
                    success=False,
                    error=error_msg,
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
    
    def detect_framework(self, project_path: str) -> str:
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
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of a file."""
        import hashlib
        if not os.path.exists(file_path):
            return ""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return ""
    
    def _compute_build_hashes(self, project_path: str) -> tuple[str, str]:
        """Compute dependency and source hashes for smart cache invalidation.
        
        Args:
            project_path: Path to project
            
        Returns:
            Tuple of (deps_hash, src_hash)
        """
        import hashlib
        
        # Dependency hash: based on lock files
        deps_files = [
            "package-lock.json",
            "yarn.lock", 
            "pnpm-lock.yaml",
            "pubspec.lock",
        ]
        deps_hash = hashlib.sha256()
        for f in deps_files:
            file_path = os.path.join(project_path, f)
            if os.path.exists(file_path):
                deps_hash.update(self._compute_file_hash(file_path).encode())
        
        # Source hash: based on key source files (fast approximation)
        src_hash = hashlib.sha256()
        key_files = ["package.json", "pubspec.yaml", "tsconfig.json", "next.config.js", "vite.config.ts"]
        for f in key_files:
            file_path = os.path.join(project_path, f)
            if os.path.exists(file_path):
                src_hash.update(self._compute_file_hash(file_path).encode())
        
        # Also hash .codi/Dockerfile if it exists
        codi_dockerfile = os.path.join(project_path, ".codi", "Dockerfile")
        if os.path.exists(codi_dockerfile):
            src_hash.update(self._compute_file_hash(codi_dockerfile).encode())
        
        return deps_hash.hexdigest()[:16], src_hash.hexdigest()[:16]
    
    def _get_image_hashes(self, image_tag: str) -> tuple[str, str]:
        """Get stored build hashes from image labels.
        
        Returns:
            Tuple of (deps_hash, src_hash) or ("", "") if image doesn't exist
        """
        try:
            image = self.client.images.get(image_tag)
            labels = image.labels or {}
            return labels.get("codi.deps_hash", ""), labels.get("codi.src_hash", "")
        except ImageNotFound:
            return "", ""
        except Exception:
            return "", ""
    
    def should_skip_build(self, project_path: str, image_tag: str) -> tuple[bool, str]:
        """Check if build can be skipped based on hash comparison.
        
        Args:
            project_path: Path to project
            image_tag: Target image tag
            
        Returns:
            Tuple of (should_skip, reason)
        """
        current_deps, current_src = self._compute_build_hashes(project_path)
        stored_deps, stored_src = self._get_image_hashes(image_tag)
        
        if not stored_deps and not stored_src:
            return False, "no previous build found"
        
        if current_deps == stored_deps and current_src == stored_src:
            return True, "no changes detected (deps and src unchanged)"
        
        if current_deps != stored_deps:
            return False, "dependency files changed - full rebuild needed"
        
        return False, "source files changed - incremental rebuild"
    
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
                    log_config={"Type": "json-file", "Config": {}},
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
    
    async def wait_for_container_healthy(self, container_id: str, timeout: int = 60) -> bool:
        """Wait for container to become healthy.
        
        Args:
            container_id: Container ID or name
            timeout: Maximum seconds to wait
            
        Returns:
            True if healthy, False if timed out or failed
        """
        logger.info(f"Waiting for container {container_id} to be healthy (timeout={timeout}s)")
        
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                loop = asyncio.get_event_loop()
                container = await loop.run_in_executor(
                    None, 
                    lambda: self.client.containers.get(container_id)
                )
                
                # Check for health status if defined
                health = container.attrs.get('State', {}).get('Health', {})
                if health:
                    status = health.get('Status')
                    if status == 'healthy':
                        logger.info(f"Container {container_id} is healthy")
                        return True
                    if status == 'unhealthy':
                        logger.error(f"Container {container_id} is unhealthy")
                        return False
                    # Still starting...
                else:
                    # No health check defined, fallback to running status
                    if container.status == 'running':
                        logger.info(f"Container {container_id} is running (no health check defined)")
                        # Wait a bit more to be sure
                        await asyncio.sleep(2)
                        return True
                
            except NotFound:
                logger.error(f"Container {container_id} not found while waiting for health")
                return False
            except Exception as e:
                logger.warning(f"Error checking container health: {e}")
            
            await asyncio.sleep(1)
            
        logger.warning(f"Timed out waiting for container {container_id} to be healthy")
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
            
            # Run the blocking log stream in a thread
            import asyncio
            import queue
            import threading
            
            log_queue: queue.Queue = queue.Queue()
            stop_event = threading.Event()
            
            def stream_in_thread():
                try:
                    for chunk in container.logs(**kwargs):
                        if stop_event.is_set():
                            break
                        if isinstance(chunk, bytes):
                            log_queue.put(chunk.decode("utf-8", errors="replace"))
                        else:
                            log_queue.put(str(chunk))
                except Exception as e:
                    log_queue.put(None)  # Signal completion
                finally:
                    log_queue.put(None)  # Signal completion
            
            # Start streaming thread
            thread = threading.Thread(target=stream_in_thread, daemon=True)
            thread.start()
            
            # Yield logs as they become available
            try:
                while True:
                    try:
                        # Check queue with timeout to allow async cancellation
                        log_line = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: log_queue.get(timeout=0.5)
                        )
                        if log_line is None:
                            break
                        yield log_line
                    except queue.Empty:
                        # No log line yet, continue waiting
                        await asyncio.sleep(0.1)
            finally:
                stop_event.set()
                    
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
