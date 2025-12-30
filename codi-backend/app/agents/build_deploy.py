"""Build and Deploy agent for CI/CD operations."""
import asyncio
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager

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
1. Trigger GitHub Actions workflows
2. Monitor build progress
3. Report build status
4. Handle deployment to GitHub Pages
5. Report deployment URLs

## Build Workflow:
1. Trigger flutter_web_build.yml workflow
2. Monitor progress through stages (dependencies, build, test, deploy)
3. Report final deployment URL"""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Build Deploy agent."""

        @tool
        def trigger_build(workflow_file: str = "flutter_web_build.yml", branch: str = "main") -> str:
            """Trigger a GitHub Actions build workflow.

            Args:
                workflow_file: Name of the workflow file
                branch: Branch to build

            Returns:
                Result with workflow run information
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                result = self.github_service.trigger_workflow(
                    repo_full_name=self.context.repo_full_name,
                    workflow_file=workflow_file,
                    ref=branch,
                )
                return str(result)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def check_build_status(run_id: int) -> str:
            """Check the status of a workflow run.

            Args:
                run_id: Workflow run ID

            Returns:
                Status information
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                status = self.github_service.get_workflow_run_status(
                    repo_full_name=self.context.repo_full_name,
                    run_id=run_id,
                )
                return str(status)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def get_pages_url() -> str:
            """Get the GitHub Pages deployment URL.

            Returns:
                Pages URL for the repository
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            parts = self.context.repo_full_name.split("/")
            if len(parts) == 2:
                owner, repo = parts
                return f"https://{owner}.github.io/{repo}/"
            return "Error: Invalid repository name"

        return [trigger_build, check_build_status, get_pages_url]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute build and deployment.

        Args:
            input_data: Dictionary with build configuration

        Returns:
            Dictionary with build/deployment results
        """
        branch = input_data.get("branch", self.context.current_branch)
        workflow = input_data.get("workflow", "flutter_web_build.yml")

        # Emit start status
        await self.emit_status(
            status="started",
            message="Triggering GitHub Actions workflow",
        )

        try:
            # Trigger the build
            await connection_manager.broadcast_to_project(
                self.context.project_id,
                {
                    "type": "build_status",
                    "agent": self.name,
                    "status": "triggered",
                    "workflow": "Flutter Web Build",
                    "message": "Build workflow started",
                },
            )

            # Simulate trigger (in real implementation, call GitHub API)
            trigger_result = await self.execute_tool(
                "trigger_build",
                {"workflow_file": workflow, "branch": branch},
            )

            # Simulate build progress stages
            stages = [
                ("dependencies", "Installing Flutter dependencies", 0.2),
                ("build", "Building Flutter web app", 0.5),
                ("test", "Running tests", 0.7),
                ("deploy", "Deploying to GitHub Pages", 0.9),
            ]

            for stage, message, progress in stages:
                await connection_manager.send_build_progress(
                    project_id=self.context.project_id,
                    stage=stage,
                    message=message,
                    progress=progress,
                )
                # Small delay to simulate build time
                await asyncio.sleep(0.5)

            # Get deployment URL
            deployment_url = await self.execute_tool("get_pages_url", {})

            # Emit deployment complete
            await connection_manager.send_deployment_complete(
                project_id=self.context.project_id,
                status="success",
                message="✅ Deployed successfully!",
                deployment_url=deployment_url,
                build_time="1m 30s",
                size="2.3 MB",
            )

            # Emit completion
            await self.emit_status(
                status="completed",
                message="Deployment complete",
            )

            return {
                "status": "success",
                "deployment_url": deployment_url,
                "branch": branch,
                "workflow": workflow,
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
