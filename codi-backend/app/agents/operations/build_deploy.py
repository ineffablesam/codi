"""Build and Deploy agent for CI/CD operations."""
import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class BuildDeployAgent(BaseAgent):
    """Agent responsible for CI/CD operations.

    The Build Deploy agent triggers GitHub Actions workflows,
    monitors build progress, and handles deployments.
    """

    name = "build_deploy"
    description = "CI/CD orchestration for builds and deployments"

    system_prompt = """You are the Build & Deploy Agent for Codi, an AI-powered Flutter development platform.

Your role is to manage the build and deployment pipeline.

## Your Responsibilities:
1. Build Docker images for projects
2. Manage container lifecycle (start, stop, restart)
3. Monitor build and deployment progress
4. Report deployment URLs (local Traefik-based)
5. Provide container logs for debugging

## Local Docker Workflow:
1. Build image using framework-specific Dockerfile
2. Create and start container with Traefik labels
3. Monitor progress through Docker events
4. Report final local URL (e.g., project-slug.localhost)
"""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Build Deploy agent."""

        @tool
        async def build_and_deploy(image_tag: str, framework: str = "auto") -> str:
            """Build and deploy a project locally using Docker.

            Args:
                image_tag: Tag for the Docker image
                framework: Project framework (flutter, nextjs, react, etc.)

            Returns:
                Result of the build and deployment
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                # Build image
                build_result = await self.docker_service.build_image(
                    project_path=self.context.project_folder,
                    image_tag=image_tag,
                    framework=framework,
                )

                if not build_result.success:
                    return f"Build failed: {build_result.error}"

                # Create and start container
                container_name = f"codi-{self.context.project_id}"
                # Simplified Traefik labels for local dev
                labels = {
                    "traefik.enable": "true",
                    f"traefik.http.routers.{container_name}.rule": f"Host(`{container_name}.localhost`)",
                }

                container_info = await self.docker_service.create_container(
                    image=image_tag,
                    name=container_name,
                    labels=labels,
                )

                return json.dumps({
                    "success": True,
                    "image_id": build_result.image_id,
                    "container_id": container_info.id,
                    "url": f"http://{container_name}.localhost",
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        async def get_container_status() -> str:
            """Check the status of the project container.

            Returns:
                Container status information
            """
            container_name = f"codi-{self.context.project_id}"
            try:
                info = await self.docker_service.get_container(container_name)
                if not info:
                    return "Container not found"
                return json.dumps(info.__dict__, default=str)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def get_local_url() -> str:
            """Get the local deployment URL.

            Returns:
                Local Traefik-based URL
            """
            container_name = f"codi-{self.context.project_id}"
            return f"http://{container_name}.localhost"

        return [build_and_deploy, get_container_status, get_local_url]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute build and deployment.

        Args:
            input_data: Dictionary with build configuration

        Returns:
            Dictionary with build/deployment results
        """
        framework = input_data.get("framework", "auto")
        image_tag = f"codi/project-{self.context.project_id}:latest"

        # Emit start status
        await self.emit_status(
            status="started",
            message="Starting local Docker build and deployment",
        )

        try:
            # Trigger the build
            await connection_manager.broadcast_to_project(
                self.context.project_id,
                {
                    "type": "build_status",
                    "agent": self.name,
                    "status": "triggered",
                    "workflow": "Local Docker Build",
                    "message": "Local build started",
                },
            )

            # Build and deploy
            result_str = await self.execute_tool(
                "build_and_deploy",
                {"image_tag": image_tag, "framework": framework},
            )

            if result_str.startswith("Error"):
                raise ValueError(result_str)

            result_data = json.loads(result_str)
            deployment_url = result_data.get("url")

            # Emit deployment complete
            await connection_manager.send_deployment_complete(
                project_id=self.context.project_id,
                status="success",
                message="✅ Deployed locally to Docker!",
                deployment_url=deployment_url,
                build_time="Local build complete",
                size="N/A",
            )

            # Emit completion
            await self.emit_status(
                status="completed",
                message="Local deployment complete",
            )

            return {
                "status": "success",
                "deployment_url": deployment_url,
                "image_id": result_data.get("image_id"),
                "container_id": result_data.get("container_id"),
            }

        except Exception as e:
            logger.error(f"Build/Deploy failed: {e}")
            await connection_manager.send_deployment_complete(
                project_id=self.context.project_id,
                status="failed",
                message=f"❌ Deployment failed: {e}",
            )
            await self.emit_error(
                error=str(e),
                message="Build/Deploy failed",
            )
            raise
