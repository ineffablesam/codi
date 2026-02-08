"""Docker Compose service for managing multi-service projects."""
import asyncio
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ComposeService:
    """Represents a service in docker-compose."""
    name: str
    status: str  # running, exited, restarting, etc.
    health: Optional[str] = None  # healthy, unhealthy, starting, none


class DockerComposeService:
    """Service for managing docker-compose projects."""

    @staticmethod
    def detect_compose_file(project_path: str) -> Optional[str]:
        """Detect docker-compose file in project.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            Path to docker-compose file if found, None otherwise
        """
        project_dir = Path(project_path)
        
        # Check for common docker-compose file names
        for filename in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            compose_file = project_dir / filename
            if compose_file.exists():
                return str(compose_file)
        
        return None

    @staticmethod
    async def compose_up(
        project_path: str,
        env_vars: Optional[Dict[str, str]] = None,
        detach: bool = True,
        build: bool = True,
    ) -> tuple[bool, str]:
        """Start all services defined in docker-compose.yml.
        
        Args:
            project_path: Path to project directory
            env_vars: Additional environment variables
            detach: Run in detached mode
            build: Build images before starting
            
        Returns:
            Tuple of (success, output)
        """
        try:
            compose_file = DockerComposeService.detect_compose_file(project_path)
            if not compose_file:
                return False, "No docker-compose.yml file found"
            
            cmd = ["docker-compose"]
            
            # Build command
            args = ["up"]
            if detach:
                args.append("-d")
            if build:
                args.append("--build")
            
            cmd.extend(args)
            
            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
            
            # Run docker-compose up
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            if process.returncode == 0:
                logger.info(f"Docker Compose up successful for {project_path}")
                return True, output
            else:
                logger.error(f"Docker Compose up failed: {output}")
                return False, output
                
        except Exception as e:
            logger.error(f"Error running docker-compose up: {e}")
            return False, str(e)

    @staticmethod
    async def compose_down(project_path: str, remove_volumes: bool = False) -> tuple[bool, str]:
        """Stop and remove all services.
        
        Args:
            project_path: Path to project directory
            remove_volumes: Remove named volumes
            
        Returns:
            Tuple of (success, output)
        """
        try:
            cmd = ["docker-compose", "down"]
            if remove_volumes:
                cmd.append("-v")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            return process.returncode == 0, output
            
        except Exception as e:
            logger.error(f"Error running docker-compose down: {e}")
            return False, str(e)

    @staticmethod
    async def compose_ps(project_path: str) -> List[ComposeService]:
        """Get status of all services.
        
        Args:
            project_path: Path to project directory
            
        Returns:
            List of ComposeService objects
        """
        try:
            # Use docker-compose ps with format
            process = await asyncio.create_subprocess_exec(
                "docker-compose", "ps", "--format", "json",
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Error getting compose services: {stderr.decode()}")
                return []
            
            # Parse JSON output
            import json
            services = []
            for line in stdout.decode().strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    services.append(ComposeService(
                        name=data.get("Service", ""),
                        status=data.get("State", "unknown"),
                        health=data.get("Health", None),
                    ))
                except json.JSONDecodeError:
                    continue
            
            return services
            
        except Exception as e:
            logger.error(f"Error getting compose services: {e}")
            return []

    @staticmethod
    async def compose_logs(
        project_path: str,
        service: Optional[str] = None,
        tail: int = 100,
    ) -> str:
        """Get logs from services.
        
        Args:
            project_path: Path to project directory
            service: Specific service name (None for all)
            tail: Number of lines to show
            
        Returns:
            Log output
        """
        try:
            cmd = ["docker-compose", "logs", "--tail", str(tail)]
            if service:
                cmd.append(service)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            return stdout.decode() + stderr.decode()
            
        except Exception as e:
            logger.error(f"Error getting compose logs: {e}")
            return str(e)

    @staticmethod
    async def wait_for_services_healthy(
        project_path: str,
        timeout: int = 120,
        check_interval: int = 5,
    ) -> tuple[bool, str]:
        """Wait for all services to be healthy.
        
        Args:
            project_path: Path to project directory
            timeout: Maximum time to wait in seconds
            check_interval: Seconds between health checks
            
        Returns:
            Tuple of (all_healthy, message)
        """
        elapsed = 0
        
        while elapsed < timeout:
            services = await DockerComposeService.compose_ps(project_path)
            
            if not services:
                return False, "No services found"
            
            # Check if all services are running
            all_running = all(s.status == "running" for s in services)
            
            if all_running:
                # Check health status for services with health checks
                services_with_health = [s for s in services if s.health is not None]
                
                if services_with_health:
                    all_healthy = all(s.health == "healthy" for s in services_with_health)
                    if all_healthy:
                        return True, "All services are healthy"
                else:
                    # No health checks defined, just check if running
                    return True, "All services are running"
            
            # Check for failed services
            failed = [s for s in services if s.status in ["exited", "dead"]]
            if failed:
                failed_names = ", ".join(s.name for s in failed)
                return False, f"Services failed: {failed_names}"
            
            # Wait before next check
            await asyncio.sleep(check_interval)
            elapsed += check_interval
        
        # Timeout reached
        services = await DockerComposeService.compose_ps(project_path)
        status_summary = "\n".join(f"  {s.name}: {s.status} (health: {s.health or 'none'})" for s in services)
        return False, f"Timeout waiting for services to be healthy:\n{status_summary}"

    @staticmethod
    async def compose_restart(project_path: str, service: Optional[str] = None) -> tuple[bool, str]:
        """Restart services.
        
        Args:
            project_path: Path to project directory
            service: Specific service to restart (None for all)
            
        Returns:
            Tuple of (success, output)
        """
        try:
            cmd = ["docker-compose", "restart"]
            if service:
                cmd.append(service)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode() + stderr.decode()
            
            return process.returncode == 0, output
            
        except Exception as e:
            logger.error(f"Error restarting compose services: {e}")
            return False, str(e)
