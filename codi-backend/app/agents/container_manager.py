"""Container Manager Agent - Docker container lifecycle management.

Model: gemini-2.5-flash
Role: Manages Docker container lifecycle for project deployments.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.config import settings
from app.models.container import ContainerStatus
from app.models.deployment import DeploymentStatus
from app.services.docker_service import get_docker_service
from app.services.traefik_service import get_traefik_service
from app.services.framework_detector import detect_framework
from app.utils.logging import get_logger

logger = get_logger(__name__)


CONTAINER_MANAGER_PROMPT = """You are "Container Manager" - Codi's Docker Container Lifecycle Agent.

## IDENTITY
You manage Docker containers for project builds and deployments. You can build images,
create containers, start/stop/restart them, and manage routing.

## CORE CAPABILITIES
1. **Build Images**: Build Docker images from project source
2. **Container Lifecycle**: Create, start, stop, restart, destroy containers
3. **Log Management**: Retrieve and stream container logs
4. **Resource Monitoring**: Get CPU/memory/network stats
5. **Routing**: Configure Traefik labels for subdomain access

## OPERATING PRINCIPLES

### Container Naming Convention
- Production: `codi-{project_slug}`
- Preview: `codi-{project_slug}-preview-{branch}`

### Image Tagging Convention
- Production: `codi/{project_slug}:latest`
- Preview: `codi/{project_slug}:{branch}`
- Commit-specific: `codi/{project_slug}:{commit_sha[:7]}`

### Resource Defaults
- CPU: 0.5 (50% of one CPU)
- Memory: 512MB
- Network: codi-network (for Traefik routing)

## WORKFLOW

### Deploy New Version
1. Stop existing container (if any)
2. Build new image from source
3. Create new container with Traefik labels
4. Start container
5. Verify health check

### Create Preview
1. Build image with branch tag
2. Create container with preview subdomain
3. Start container
4. Return preview URL

## RESPONSE FORMAT
Always return structured responses with:
- `success`: boolean
- `container_id`: string (if applicable)
- `image_tag`: string (if applicable)
- `url`: string (if applicable)
- `message`: string describing what was done
- `logs`: array of relevant log lines (if applicable)
"""


class ContainerManagerAgent(BaseAgent):
    """Docker container lifecycle management agent.
    
    Handles building images, managing containers, and configuring routing.
    """
    
    name = "container_manager"
    description = "Manages Docker containers for project builds and deployments"
    system_prompt = CONTAINER_MANAGER_PROMPT
    
    # Model configuration
    model_provider = "gemini"
    model_name = "gemini-2.5-flash-preview-05-20"
    
    def __init__(self, context: AgentContext) -> None:
        super().__init__(context)
        self._docker_service = get_docker_service()
        self._traefik_service = get_traefik_service()
    
    def get_tools(self) -> List[BaseTool]:
        """Return container management tools."""
        return [
            self._create_build_image_tool(),
            self._create_create_container_tool(),
            self._create_start_container_tool(),
            self._create_stop_container_tool(),
            self._create_restart_container_tool(),
            self._create_destroy_container_tool(),
            self._create_get_logs_tool(),
            self._create_get_stats_tool(),
        ]
    
    def _create_build_image_tool(self) -> BaseTool:
        """Create tool to build Docker image."""
        context = self.context
        docker_svc = self._docker_service
        
        @tool
        async def build_image(
            framework: str = "auto",
            image_tag: Optional[str] = None,
        ) -> str:
            """Build a Docker image from the project source.
            
            Args:
                framework: Framework type (flutter, nextjs, react, react_native, auto)
                image_tag: Optional custom image tag
            """
            if not context.project_folder:
                return "Error: No project folder configured"
            
            try:
                # Auto-detect framework if needed
                if framework == "auto":
                    detected = detect_framework(context.project_folder)
                    framework = detected.framework.value
                
                # Generate image tag
                if not image_tag:
                    # TODO: Get project slug from context
                    project_slug = context.project_folder.split("/")[-1]
                    image_tag = f"codi/{project_slug}:latest"
                
                result = await docker_svc.build_image(
                    project_path=context.project_folder,
                    image_tag=image_tag,
                    framework=framework,
                )
                
                if result.success:
                    return f"Successfully built image {image_tag}\n\nBuild logs (last 10 lines):\n" + "\n".join(result.build_logs[-10:])
                else:
                    return f"Build failed: {result.error}\n\nBuild logs:\n" + "\n".join(result.build_logs[-20:])
                    
            except Exception as e:
                return f"Error building image: {e}"
        
        return build_image
    
    def _create_create_container_tool(self) -> BaseTool:
        """Create tool to create a container."""
        context = self.context
        docker_svc = self._docker_service
        traefik_svc = self._traefik_service
        
        @tool
        async def create_container(
            image: str,
            name: str,
            is_preview: bool = False,
            branch: Optional[str] = None,
            port: int = 80,
        ) -> str:
            """Create a new Docker container with Traefik routing.
            
            Args:
                image: Docker image to use
                name: Container name
                is_preview: Whether this is a preview deployment
                branch: Branch name for preview routing
                port: Container port to expose
            """
            try:
                # Generate Traefik labels
                project_slug = name.replace("codi-", "").split("-preview-")[0]
                labels = traefik_svc.generate_labels(
                    project_slug=project_slug,
                    container_name=name,
                    port=port,
                    is_preview=is_preview,
                    branch=branch,
                )
                
                # Create container
                container_info = await docker_svc.create_container(
                    image=image,
                    name=name,
                    labels=labels,
                    cpu_limit=docker_svc.DEFAULT_CPU_LIMIT,
                    memory_limit=docker_svc.DEFAULT_MEMORY_LIMIT,
                    auto_start=True,
                )
                
                # Get URL
                url = traefik_svc.get_subdomain_url(project_slug, is_preview, branch)
                
                return f"Created and started container {name}\nID: {container_info.short_id}\nStatus: {container_info.status.value}\nURL: {url}"
                
            except Exception as e:
                return f"Error creating container: {e}"
        
        return create_container
    
    def _create_start_container_tool(self) -> BaseTool:
        """Create tool to start a container."""
        docker_svc = self._docker_service
        
        @tool
        async def start_container(container_id: str) -> str:
            """Start a stopped container.
            
            Args:
                container_id: Container ID or name
            """
            try:
                info = await docker_svc.start_container(container_id)
                return f"Started container {container_id}\nStatus: {info.status.value}"
            except Exception as e:
                return f"Error starting container: {e}"
        
        return start_container
    
    def _create_stop_container_tool(self) -> BaseTool:
        """Create tool to stop a container."""
        docker_svc = self._docker_service
        
        @tool
        async def stop_container(container_id: str, timeout: int = 10) -> str:
            """Stop a running container.
            
            Args:
                container_id: Container ID or name
                timeout: Seconds to wait before SIGKILL
            """
            try:
                info = await docker_svc.stop_container(container_id, timeout=timeout)
                return f"Stopped container {container_id}\nStatus: {info.status.value}"
            except Exception as e:
                return f"Error stopping container: {e}"
        
        return stop_container
    
    def _create_restart_container_tool(self) -> BaseTool:
        """Create tool to restart a container."""
        docker_svc = self._docker_service
        
        @tool
        async def restart_container(container_id: str) -> str:
            """Restart a container.
            
            Args:
                container_id: Container ID or name
            """
            try:
                info = await docker_svc.restart_container(container_id)
                return f"Restarted container {container_id}\nStatus: {info.status.value}"
            except Exception as e:
                return f"Error restarting container: {e}"
        
        return restart_container
    
    def _create_destroy_container_tool(self) -> BaseTool:
        """Create tool to destroy a container."""
        docker_svc = self._docker_service
        
        @tool
        async def destroy_container(container_id: str, force: bool = True) -> str:
            """Destroy (remove) a container.
            
            Args:
                container_id: Container ID or name
                force: Force remove even if running
            """
            try:
                success = await docker_svc.remove_container(container_id, force=force)
                if success:
                    return f"Destroyed container {container_id}"
                else:
                    return f"Container {container_id} not found or already removed"
            except Exception as e:
                return f"Error destroying container: {e}"
        
        return destroy_container
    
    def _create_get_logs_tool(self) -> BaseTool:
        """Create tool to get container logs."""
        docker_svc = self._docker_service
        
        @tool
        async def get_container_logs(container_id: str, tail: int = 50) -> str:
            """Get recent logs from a container.
            
            Args:
                container_id: Container ID or name
                tail: Number of lines to return
            """
            try:
                logs = await docker_svc.get_container_logs(container_id, tail=tail)
                if logs:
                    return f"Last {tail} lines from {container_id}:\n\n" + "\n".join(logs[:tail])
                return f"No logs found for {container_id}"
            except Exception as e:
                return f"Error getting logs: {e}"
        
        return get_container_logs
    
    def _create_get_stats_tool(self) -> BaseTool:
        """Create tool to get container stats."""
        docker_svc = self._docker_service
        
        @tool
        async def get_container_stats(container_id: str) -> str:
            """Get resource usage stats for a container.
            
            Args:
                container_id: Container ID or name
            """
            try:
                stats = await docker_svc.get_container_stats(container_id)
                return f"""Container Stats for {container_id}:
- CPU: {stats.cpu_percent}%
- Memory: {stats.memory_usage_mb}MB / {stats.memory_limit_mb}MB ({stats.memory_percent}%)
- Network RX: {stats.network_rx_bytes / 1024:.2f} KB
- Network TX: {stats.network_tx_bytes / 1024:.2f} KB
- Timestamp: {stats.timestamp.isoformat()}"""
            except Exception as e:
                return f"Error getting stats: {e}"
        
        return get_container_stats
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the Container Manager agent.
        
        Args:
            input_data: Should contain 'operation' and operation-specific params
            
        Returns:
            Operation result
        """
        await self.emit_status("started", "Container Manager processing request...")
        
        operation = input_data.get("operation", "")
        
        # Build prompt based on operation
        prompt_parts = [f"## Operation Request\n{operation}"]
        
        if input_data.get("project_slug"):
            prompt_parts.append(f"Project: {input_data['project_slug']}")
        if input_data.get("branch"):
            prompt_parts.append(f"Branch: {input_data['branch']}")
        if input_data.get("framework"):
            prompt_parts.append(f"Framework: {input_data['framework']}")
        
        prompt_parts.append("\n\nExecute the requested operation using available tools.")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content="\n".join(prompt_parts)),
        ]
        
        try:
            llm_with_tools = self.llm.bind_tools(self.tools)
            response = await llm_with_tools.ainvoke(messages)
            
            result = {
                "agent": self.name,
                "operation": operation,
                "result": response.content,
            }
            
            await self.emit_status("completed", "Container operation complete")
            return result
            
        except Exception as e:
            logger.error(f"Container Manager failed: {e}")
            await self.emit_error(str(e), "Container operation failed")
            raise
    
    async def deploy(
        self,
        project_slug: str,
        framework: str = "auto",
        is_preview: bool = False,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Deploy a project container.
        
        High-level method that orchestrates the full deployment flow.
        
        Args:
            project_slug: URL-safe project identifier
            framework: Framework type or 'auto' to detect
            is_preview: Whether this is a preview deployment
            branch: Git branch
            
        Returns:
            Deployment result with URL
        """
        await self.emit_status("started", f"Deploying {project_slug}...")
        
        try:
            # Detect framework if auto
            if framework == "auto" and self.context.project_folder:
                detected = detect_framework(self.context.project_folder)
                framework = detected.framework.value
            
            # Generate names
            if is_preview:
                container_name = f"codi-{project_slug}-preview-{branch}"
                image_tag = f"codi/{project_slug}:{branch}"
            else:
                container_name = f"codi-{project_slug}"
                image_tag = f"codi/{project_slug}:latest"
            
            # Build image
            await self.emit_status("in_progress", "Building Docker image...")
            build_result = await self._docker_service.build_image(
                project_path=self.context.project_folder,
                image_tag=image_tag,
                framework=framework,
            )
            
            if not build_result.success:
                raise RuntimeError(f"Build failed: {build_result.error}")
            
            # Stop existing container if any
            existing = await self._docker_service.get_container(container_name)
            if existing:
                await self.emit_status("in_progress", "Stopping existing container...")
                await self._docker_service.stop_container(container_name)
                await self._docker_service.remove_container(container_name)
            
            # Get port for framework
            port = self._traefik_service.get_port_for_framework(framework)
            
            # Generate Traefik labels
            labels = self._traefik_service.generate_labels(
                project_slug=project_slug,
                container_name=container_name,
                port=port,
                is_preview=is_preview,
                branch=branch if is_preview else None,
            )
            
            # Create and start container
            await self.emit_status("in_progress", "Starting container...")
            container_info = await self._docker_service.create_container(
                image=image_tag,
                name=container_name,
                labels=labels,
                auto_start=True,
            )
            
            # Get URL
            url = self._traefik_service.get_subdomain_url(project_slug, is_preview, branch if is_preview else None)
            
            await self.emit_status("completed", f"Deployed to {url}")
            
            return {
                "success": True,
                "container_id": container_info.id,
                "container_name": container_name,
                "image_tag": image_tag,
                "url": url,
                "status": container_info.status.value,
            }
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            await self.emit_error(str(e), "Deployment failed")
            return {
                "success": False,
                "error": str(e),
            }
