"""Git Operator agent for version control operations."""
import json
from typing import Any, Dict, List

from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.utils.logging import get_logger
from app.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class GitOperatorAgent(BaseAgent):
    """Agent responsible for Git operations.

    The Git Operator handles all version control tasks including
    creating branches, committing changes, and pushing to GitHub.
    """

    name = "git_operator"
    description = "Version control operations"

    system_prompt = """You are the Git Operator Agent for Codi, an AI-powered Flutter development platform.

Your role is to manage version control operations for the project.

## Your Responsibilities:
1. Create feature branches for new work
2. Commit changes with semantic, descriptive messages
3. Push branches to GitHub
4. Handle merge operations
5. Maintain clean git history

## Branching Strategy:
- feature/ - New features
- fix/ - Bug fixes
- refactor/ - Code refactoring
- docs/ - Documentation

## Commit Message Format:
Use conventional commits:
- feat: Add new feature
- fix: Fix bug
- refactor: Refactor code
- docs: Update documentation
- style: Code style changes
- test: Add tests
- chore: Maintenance tasks"""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Git operator."""

        @tool
        def create_branch(branch_name: str, from_branch: str = "main") -> str:
            """Create a new branch.

            Args:
                branch_name: Name of the new branch
                from_branch: Base branch to create from

            Returns:
                Result of the operation
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                result = self.github_service.create_branch(
                    repo_full_name=self.context.repo_full_name,
                    branch_name=branch_name,
                    from_branch=from_branch,
                )
                return json.dumps(result)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def commit_file(file_path: str, content: str, message: str) -> str:
            """Commit a file change.

            Args:
                file_path: Path to the file
                content: New file content
                message: Commit message

            Returns:
                Result of the operation
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                result = self.github_service.create_or_update_file(
                    repo_full_name=self.context.repo_full_name,
                    file_path=file_path,
                    content=content,
                    commit_message=message,
                    branch=self.context.current_branch,
                )
                return json.dumps(result)
            except Exception as e:
                return f"Error: {e}"

        @tool
        def commit_multiple_files(files_json: str, message: str) -> str:
            """Commit multiple files in a single commit.

            Args:
                files_json: JSON array of objects with 'path' and 'content' keys
                message: Commit message

            Returns:
                Result of the operation
            """
            if not self.context.repo_full_name:
                return "Error: No repository configured"

            try:
                files = json.loads(files_json)
                result = self.github_service.commit_multiple_files(
                    repo_full_name=self.context.repo_full_name,
                    files=files,
                    commit_message=message,
                    branch=self.context.current_branch,
                )
                return json.dumps(result)
            except Exception as e:
                return f"Error: {e}"

        return [create_branch, commit_file, commit_multiple_files]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute git operations.

        Args:
            input_data: Dictionary with operation details

        Returns:
            Dictionary with operation results
        """
        operation = input_data.get("operation", "commit")
        files = input_data.get("files", [])
        commit_message = input_data.get("message", "Update files")
        branch_name = input_data.get("branch_name")

        # Emit start status
        await self.emit_status(
            status="started",
            message="Preparing to commit changes",
        )

        try:
            # Create branch if specified
            if branch_name and branch_name != self.context.current_branch:
                await connection_manager.send_git_operation(
                    project_id=self.context.project_id,
                    operation="create_branch",
                    message=f"Creating branch: {branch_name}",
                    branch_name=branch_name,
                )

                result = await self.execute_tool(
                    "create_branch",
                    {
                        "branch_name": branch_name,
                        "from_branch": self.context.current_branch,
                    },
                )

                # Update context
                self.context.current_branch = branch_name

            # Commit files
            if files:
                total_insertions = 0
                total_deletions = 0

                for file_info in files:
                    file_path = file_info.get("path", "")
                    content = file_info.get("content", "")
                    lines = len(content.split("\n"))
                    total_insertions += lines

                # Commit all files
                files_json = json.dumps(files)
                result = await self.execute_tool(
                    "commit_multiple_files",
                    {
                        "files_json": files_json,
                        "message": commit_message,
                    },
                )

                result_data = json.loads(result) if isinstance(result, str) else result
                commit_sha = result_data.get("commit_sha", "")[:7]

                # Emit git operation
                await connection_manager.send_git_operation(
                    project_id=self.context.project_id,
                    operation="commit",
                    message=commit_message,
                    commit_sha=commit_sha,
                    branch_name=self.context.current_branch,
                    files_changed=len(files),
                    insertions=total_insertions,
                    deletions=total_deletions,
                )

                # Emit push notification
                await connection_manager.send_git_operation(
                    project_id=self.context.project_id,
                    operation="push",
                    message=f"Pushed to {self.context.current_branch}",
                    branch_name=self.context.current_branch,
                    commit_sha=commit_sha,
                )

            # Emit completion
            await self.emit_status(
                status="completed",
                message="✅ Changes committed and pushed",
                details={
                    "branch": self.context.current_branch,
                    "files_changed": len(files),
                    "commit_message": commit_message,
                },
            )

            return {
                "branch": self.context.current_branch,
                "files_committed": len(files),
                "commit_message": commit_message,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Git operation failed: {e}")
            await self.emit_error(
                error=str(e),
                message="Git operation failed",
            )
            raise
