"""Git Operator agent for local version control operations.

Manages local Git repositories using GitPython. No external GitHub dependency.
"""
import json
from typing import Any, Dict, List

from langchain_core.tools import BaseTool, tool

from app.agents.base import AgentContext, BaseAgent
from app.services.infrastructure.git import LocalGitService, get_git_service
from app.utils.logging import get_logger
from app.api.websocket.connection_manager import connection_manager

logger = get_logger(__name__)


class GitOperatorAgent(BaseAgent):
    """Agent responsible for local Git operations.

    The Git Operator handles all version control tasks including
    creating branches, committing changes, and managing local repositories.
    All operations are local - no GitHub/external API dependency.
    """

    name = "git_operator"
    description = "Local version control operations"

    system_prompt = """You are the Git Operator Agent for Codi, an AI-powered development platform.

Your role is to manage local version control operations for the project.

## Your Responsibilities:
1. Create feature branches for new work
2. Commit changes with semantic, descriptive messages
3. Manage branch operations (checkout, merge)
4. Handle rollbacks via git reset
5. Maintain clean git history

## Branching Strategy:
- feature/ - New features
- fix/ - Bug fixes
- refactor/ - Code refactoring
- docs/ - Documentation
- preview/ - Preview deployments

## Commit Message Format:
Use conventional commits:
- feat: Add new feature
- fix: Fix bug
- refactor: Refactor code
- docs: Update documentation
- style: Code style changes
- test: Add tests
- chore: Maintenance tasks

## LOCAL OPERATIONS ONLY:
All git operations are performed on the local filesystem.
Repositories are stored at: /var/codi/repos/{user_id}/{project_slug}
No external git hosting (GitHub, GitLab) is used."""

    def get_tools(self) -> List[BaseTool]:
        """Get tools available to the Git operator."""

        @tool
        def create_branch(branch_name: str, from_ref: str = "HEAD") -> str:
            """Create a new branch.

            Args:
                branch_name: Name of the new branch
                from_ref: Reference to create branch from (branch name or commit SHA)

            Returns:
                Result of the operation
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                result = self.git_service.create_branch(
                    branch_name=branch_name,
                    from_ref=from_ref,
                )
                return json.dumps({
                    "success": True,
                    "branch": result,
                    "from_ref": from_ref,
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def checkout_branch(ref: str) -> str:
            """Checkout a branch or commit.

            Args:
                ref: Branch name or commit SHA to checkout

            Returns:
                Result of the operation
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                commit_sha = self.git_service.checkout(ref)
                return json.dumps({
                    "success": True,
                    "ref": ref,
                    "commit_sha": commit_sha,
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def write_file(file_path: str, content: str) -> str:
            """Write content to a file in the project.

            Args:
                file_path: Path to the file within the project
                content: File content to write

            Returns:
                Result of the operation
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                full_path = self.git_service.write_file(file_path, content)
                return json.dumps({
                    "success": True,
                    "path": file_path,
                    "full_path": full_path,
                    "size": len(content),
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def read_file(file_path: str) -> str:
            """Read content from a file in the project.

            Args:
                file_path: Path to the file within the project

            Returns:
                File content or error message
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                content = self.git_service.get_file_content(file_path)
                return content
            except FileNotFoundError:
                return f"Error: File not found: {file_path}"
            except Exception as e:
                return f"Error: {e}"

        @tool
        def commit_changes(message: str, files: str = "", all_changes: bool = True) -> str:
            """Commit changes to the repository.

            Args:
                message: Commit message (use conventional commits format)
                files: Comma-separated list of specific files to commit (empty for all)
                all_changes: If True, stage all changes before committing

            Returns:
                Result of the commit operation
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                file_list = [f.strip() for f in files.split(",") if f.strip()] if files else None
                commit_info = self.git_service.commit(
                    message=message,
                    files=file_list,
                    all_changes=all_changes,
                )
                return json.dumps({
                    "success": True,
                    "sha": commit_info.sha,
                    "short_sha": commit_info.short_sha,
                    "message": commit_info.message,
                    "files_changed": commit_info.files_changed,
                    "author": commit_info.author,
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def get_status() -> str:
            """Get repository status showing staged, modified, and untracked files.

            Returns:
                JSON with status information
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                status = self.git_service.status()
                return json.dumps({
                    "success": True,
                    "staged": status["staged"],
                    "modified": status["modified"],
                    "untracked": status["untracked"],
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def get_log(n: int = 10) -> str:
            """Get commit history.

            Args:
                n: Number of commits to retrieve

            Returns:
                JSON array of commit information
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                commits = self.git_service.get_log(n=n)
                return json.dumps({
                    "success": True,
                    "commits": [
                        {
                            "sha": c.sha,
                            "short_sha": c.short_sha,
                            "message": c.message,
                            "author": c.author,
                            "timestamp": c.timestamp.isoformat(),
                            "files_changed": c.files_changed,
                        }
                        for c in commits
                    ],
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def list_branches() -> str:
            """List all branches in the repository.

            Returns:
                JSON array of branch names
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                branches = self.git_service.get_branches()
                current = self.git_service.get_current_branch()
                return json.dumps({
                    "success": True,
                    "branches": branches,
                    "current": current,
                })
            except Exception as e:
                return f"Error: {e}"

        @tool
        def reset_to_commit(commit_sha: str, hard: bool = False) -> str:
            """Reset repository to a specific commit.

            Args:
                commit_sha: Commit SHA to reset to
                hard: If True, discard all local changes

            Returns:
                Result of the reset operation
            """
            if not self.context.project_folder:
                return "Error: No project folder configured"

            try:
                new_head = self.git_service.reset(ref=commit_sha, hard=hard)
                return json.dumps({
                    "success": True,
                    "mode": "hard" if hard else "mixed",
                    "head": new_head,
                })
            except Exception as e:
                return f"Error: {e}"

        return [
            create_branch,
            checkout_branch,
            write_file,
            read_file,
            commit_changes,
            get_status,
            get_log,
            list_branches,
            reset_to_commit,
        ]

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute git operations.

        Args:
            input_data: Dictionary with operation details containing:
                - files: List of {path, content} dicts to write and commit
                - message: Commit message
                - branch_name: Optional new branch to create/switch to

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
            # Create branch if specified and different from current
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
                        "from_ref": "HEAD",
                    },
                )

                # Switch to the new branch
                await self.execute_tool(
                    "checkout_branch",
                    {"ref": branch_name},
                )

                # Update context
                self.context.current_branch = branch_name

            # Write all files to disk
            if files:
                total_insertions = 0
                total_deletions = 0

                for file_info in files:
                    file_path = file_info.get("path", "")
                    content = file_info.get("content", "")
                    
                    # Write the file
                    await self.execute_tool(
                        "write_file",
                        {
                            "file_path": file_path,
                            "content": content,
                        },
                    )
                    
                    lines = len(content.split("\n"))
                    total_insertions += lines

                # Commit all changes
                result = await self.execute_tool(
                    "commit_changes",
                    {
                        "message": commit_message,
                        "all_changes": True,
                    },
                )

                result_data = json.loads(result) if isinstance(result, str) else result
                commit_sha = result_data.get("short_sha", "")

                # Emit git operation for the commit
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

            # Emit completion
            await self.emit_status(
                status="completed",
                message="✅ Changes committed to local repository",
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
