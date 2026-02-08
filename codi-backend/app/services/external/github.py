"""GitHub service for OAuth authentication and repository operations."""
import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from github import Github, GithubException, InputGitTreeElement
from github.Repository import Repository
import nacl.encoding
import nacl.public

from app.core.config import settings
from app.services.domain.encryption import encryption_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GitHubService:
    """Service for GitHub OAuth and API operations."""

    GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_API_URL = "https://api.github.com"

    def __init__(self, access_token: Optional[str] = None) -> None:
        """Initialize GitHub service.

        Args:
            access_token: Optional GitHub access token for authenticated operations
        """
        self._access_token = access_token
        self._github: Optional[Github] = None

    @property
    def github(self) -> Github:
        """Get authenticated PyGithub instance."""
        if self._github is None:
            if self._access_token:
                self._github = Github(self._access_token)
            else:
                raise ValueError("GitHub access token not configured")
        return self._github

    @classmethod
    def get_oauth_url(cls, state: Optional[str] = None) -> str:
        """Generate GitHub OAuth authorization URL.

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            GitHub OAuth authorization URL
        """
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "user:email repo workflow",
        }
        if state:
            params["state"] = state

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{cls.GITHUB_OAUTH_URL}?{query_string}"

    @classmethod
    async def exchange_code_for_token(cls, code: str) -> Dict[str, str]:
        """Exchange OAuth authorization code for access token.

        Args:
            code: Authorization code from GitHub OAuth callback

        Returns:
            Dictionary containing access_token, token_type, and scope
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                cls.GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {response.text}")
                raise ValueError("Failed to exchange code for token")

            data = response.json()

            if "error" in data:
                logger.error(f"GitHub OAuth error: {data}")
                raise ValueError(data.get("error_description", data["error"]))

            return {
                "access_token": data["access_token"],
                "token_type": data.get("token_type", "bearer"),
                "scope": data.get("scope", ""),
            }

    @classmethod
    async def get_user_info(cls, access_token: str) -> Dict[str, Any]:
        """Get GitHub user information using access token.

        Args:
            access_token: GitHub access token

        Returns:
            Dictionary containing user information
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{cls.GITHUB_API_URL}/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

            if response.status_code != 200:
                logger.error(f"Failed to get GitHub user info: {response.text}")
                raise ValueError("Failed to get GitHub user information")

            user_data = response.json()

            # Get user's primary email if not public
            if not user_data.get("email"):
                email_response = await client.get(
                    f"{cls.GITHUB_API_URL}/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next(
                        (e["email"] for e in emails if e.get("primary")),
                        emails[0]["email"] if emails else None,
                    )
                    user_data["email"] = primary_email

            return {
                "id": user_data["id"],
                "login": user_data["login"],
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "avatar_url": user_data.get("avatar_url"),
                "html_url": user_data.get("html_url"),
            }

    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = False,
    ) -> Dict[str, Any]:
        """Create a new GitHub repository.

        Args:
            name: Repository name
            description: Optional repository description
            private: Whether the repository should be private
            auto_init: Whether to initialize with README

        Returns:
            Dictionary containing repository information
        """
        try:
            user = self.github.get_user()
            repo = user.create_repo(
                name=name,
                description=description or "",
                private=private,
                auto_init=auto_init,
            )

            logger.info(f"Created GitHub repository: {repo.full_name}")

            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "default_branch": repo.default_branch,
                "private": repo.private,
            }

        except GithubException as e:
            logger.error(f"Failed to create repository: {e}")
            raise ValueError(f"Failed to create repository: {e.data.get('message', str(e))}")

    async def enable_pages(self, repo_full_name: str) -> Dict[str, Any]:
        """Enable GitHub Pages for a repository with build_type='workflow'.

        Args:
            repo_full_name: Full repository name (owner/repo)

        Returns:
            Dictionary with Pages information
        """
        url = f"{self.GITHUB_API_URL}/repos/{repo_full_name}/pages"
        headers = {
            "Authorization": f"token {self._access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        data = {"build_type": "workflow"}

        async with httpx.AsyncClient() as client:
            try:
                # First check if it's already enabled
                check_resp = await client.get(url, headers=headers)
                if check_resp.status_code == 200:
                    logger.info(f"GitHub Pages already enabled for {repo_full_name}")
                    return check_resp.json()

                # If not enabled, create it
                response = await client.post(url, headers=headers, json=data)

                if response.status_code == 201:
                    logger.info(f"Enabled GitHub Pages for {repo_full_name}")
                    pages_data = response.json()
                    # Compute deployment URL from repo name
                    owner, repo = repo_full_name.split("/")
                    pages_data["deployment_url"] = f"https://{owner}.github.io/{repo}/"
                    return pages_data
                elif response.status_code == 409:
                    # Conflict often means already exists or in progress
                    logger.info(f"GitHub Pages conflict (already enabled?) for {repo_full_name}")
                    return {"message": "Pages already enabled or conflict"}
                else:
                    logger.error(f"Failed to enable GitHub Pages: {response.text}")
                    return {"error": response.text, "status_code": response.status_code}

            except Exception as e:
                logger.error(f"Error enabling GitHub Pages: {e}")
                return {"error": str(e)}

    async def create_webhook(
        self,
        repo_full_name: str,
        webhook_url: str,
        secret: Optional[str] = None,
        events: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a webhook for a repository.
        
        Args:
            repo_full_name: Full repository name (owner/repo)
            webhook_url: URL to receive webhook events
            secret: Optional secret for signature verification
            events: List of events to subscribe to (defaults to workflow_run, deployment_status, push)
        
        Returns:
            Dictionary with webhook information
        """
        if events is None:
            events = ["workflow_run", "deployment_status", "push"]
        
        url = f"{self.GITHUB_API_URL}/repos/{repo_full_name}/hooks"
        headers = {
            "Authorization": f"token {self._access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        
        config = {
            "url": webhook_url,
            "content_type": "json",
            "insecure_ssl": "0",
        }
        
        if secret:
            config["secret"] = secret
        
        data = {
            "name": "web",
            "active": True,
            "events": events,
            "config": config,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # Check if webhook already exists
                list_resp = await client.get(url, headers=headers)
                if list_resp.status_code == 200:
                    existing_hooks = list_resp.json()
                    for hook in existing_hooks:
                        if hook.get("config", {}).get("url") == webhook_url:
                            logger.info(f"Webhook already exists for {repo_full_name}")
                            return {"id": hook["id"], "already_exists": True}
                
                # Create webhook
                response = await client.post(url, headers=headers, json=data)
                
                if response.status_code == 201:
                    hook_data = response.json()
                    logger.info(f"Created webhook for {repo_full_name}: {hook_data['id']}")
                    return {
                        "id": hook_data["id"],
                        "url": webhook_url,
                        "events": events,
                        "active": True,
                    }
                else:
                    logger.error(f"Failed to create webhook: {response.text}")
                    return {"error": response.text, "status_code": response.status_code}
                    
            except Exception as e:
                logger.error(f"Error creating webhook: {e}")
                return {"error": str(e)}

    def get_repository(self, full_name: str) -> Repository:
        """Get a GitHub repository by full name.

        Args:
            full_name: Full repository name (owner/repo)

        Returns:
            Repository object
        """
        try:
            return self.github.get_repo(full_name)
        except GithubException as e:
            logger.error(f"Failed to get repository {full_name}: {e}")
            raise ValueError(f"Repository not found: {full_name}")

    def get_file_content(self, repo_full_name: str, file_path: str, ref: str = "main") -> str:
        """Get file content from a repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            file_path: Path to the file in the repository
            ref: Branch or commit reference

        Returns:
            File content as string
        """
        try:
            repo = self.get_repository(repo_full_name)
            contents = repo.get_contents(file_path, ref=ref)

            if isinstance(contents, list):
                raise ValueError(f"Path is a directory: {file_path}")

            return contents.decoded_content.decode("utf-8")

        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"File not found: {file_path}")
            logger.error(f"Failed to get file content: {e}")
            raise

    def create_or_update_file(
        self,
        repo_full_name: str,
        file_path: str,
        content: str,
        commit_message: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Create or update a file in the repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            file_path: Path to the file in the repository
            content: File content
            commit_message: Commit message
            branch: Branch name

        Returns:
            Dictionary with commit information
        """
        try:
            repo = self.get_repository(repo_full_name)

            # Check if file exists
            try:
                existing_file = repo.get_contents(file_path, ref=branch)
                sha = existing_file.sha if not isinstance(existing_file, list) else None
            except GithubException:
                sha = None

            if sha:
                # Update existing file
                result = repo.update_file(
                    file_path,
                    commit_message,
                    content,
                    sha,
                    branch=branch,
                )
            else:
                # Create new file
                result = repo.create_file(
                    file_path,
                    commit_message,
                    content,
                    branch=branch,
                )

            return {
                "commit_sha": result["commit"].sha,
                "file_path": file_path,
                "branch": branch,
                "message": commit_message,
            }

        except GithubException as e:
            logger.error(f"Failed to create/update file: {e}")
            raise ValueError(f"Failed to create/update file: {e.data.get('message', str(e))}")

    def delete_file(
        self,
        repo_full_name: str,
        file_path: str,
        commit_message: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Delete a file from the repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            file_path: Path to the file in the repository
            commit_message: Commit message
            branch: Branch name

        Returns:
            Dictionary with commit information
        """
        try:
            repo = self.get_repository(repo_full_name)
            contents = repo.get_contents(file_path, ref=branch)

            if isinstance(contents, list):
                raise ValueError(f"Path is a directory: {file_path}")

            result = repo.delete_file(
                file_path,
                commit_message,
                contents.sha,
                branch=branch,
            )

            return {
                "commit_sha": result["commit"].sha,
                "file_path": file_path,
                "branch": branch,
                "message": commit_message,
            }

        except GithubException as e:
            logger.error(f"Failed to delete file: {e}")
            raise ValueError(f"Failed to delete file: {e.data.get('message', str(e))}")

    def list_files(
        self,
        repo_full_name: str,
        path: str = "",
        ref: str = "main",
    ) -> List[Dict[str, Any]]:
        """List files in a repository directory.

        Args:
            repo_full_name: Full repository name (owner/repo)
            path: Directory path (empty for root)
            ref: Branch or commit reference

        Returns:
            List of file/directory information dictionaries
        """
        try:
            repo = self.get_repository(repo_full_name)
            contents = repo.get_contents(path, ref=ref)

            if not isinstance(contents, list):
                contents = [contents]

            return [
                {
                    "name": item.name,
                    "path": item.path,
                    "type": item.type,  # 'file' or 'dir'
                    "size": item.size if item.type == "file" else None,
                    "sha": item.sha,
                }
                for item in contents
            ]

        except GithubException as e:
            logger.error(f"Failed to list files: {e}")
            raise ValueError(f"Failed to list files: {e.data.get('message', str(e))}")

    def create_branch(
        self,
        repo_full_name: str,
        branch_name: str,
        from_branch: str = "main",
    ) -> Dict[str, Any]:
        """Create a new branch from an existing branch.

        Args:
            repo_full_name: Full repository name (owner/repo)
            branch_name: Name for the new branch
            from_branch: Source branch name

        Returns:
            Dictionary with branch information
        """
        try:
            repo = self.get_repository(repo_full_name)

            # Get the SHA of the source branch
            source_ref = repo.get_git_ref(f"heads/{from_branch}")
            source_sha = source_ref.object.sha

            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source_sha,
            )

            logger.info(f"Created branch {branch_name} from {from_branch}")

            return {
                "branch_name": branch_name,
                "from_branch": from_branch,
                "sha": source_sha,
            }

        except GithubException as e:
            if e.status == 422 and "Reference already exists" in str(e):
                logger.warning(f"Branch {branch_name} already exists")
                return {
                    "branch_name": branch_name,
                    "from_branch": from_branch,
                    "already_exists": True,
                }
            logger.error(f"Failed to create branch: {e}")
            raise ValueError(f"Failed to create branch: {e.data.get('message', str(e))}")

    def trigger_workflow(
        self,
        repo_full_name: str,
        workflow_file: str,
        ref: str = "main",
        inputs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow.

        Args:
            repo_full_name: Full repository name (owner/repo)
            workflow_file: Workflow filename (e.g., 'build.yml')
            ref: Branch or tag to run workflow on
            inputs: Optional workflow inputs

        Returns:
            Dictionary with workflow run information
        """
        try:
            repo = self.get_repository(repo_full_name)
            workflow = repo.get_workflow(workflow_file)

            success = workflow.create_dispatch(ref, inputs or {})

            if not success:
                raise ValueError("Failed to dispatch workflow")

            # Wait briefly and get the latest run
            import time
            time.sleep(2)

            runs = list(workflow.get_runs()[:1])
            if runs:
                run = runs[0]
                return {
                    "workflow_id": workflow.id,
                    "workflow_name": workflow.name,
                    "run_id": run.id,
                    "run_url": run.html_url,
                    "status": run.status,
                }

            return {
                "workflow_id": workflow.id,
                "workflow_name": workflow.name,
                "status": "dispatched",
            }

        except GithubException as e:
            logger.error(f"Failed to trigger workflow: {e}")
            raise ValueError(f"Failed to trigger workflow: {e.data.get('message', str(e))}")

    def get_workflow_run_status(
        self,
        repo_full_name: str,
        run_id: int,
    ) -> Dict[str, Any]:
        """Get the status of a workflow run.

        Args:
            repo_full_name: Full repository name (owner/repo)
            run_id: Workflow run ID

        Returns:
            Dictionary with run status information
        """
        try:
            repo = self.get_repository(repo_full_name)
            run = repo.get_workflow_run(run_id)

            return {
                "run_id": run.id,
                "name": run.name,
                "status": run.status,
                "conclusion": run.conclusion,
                "html_url": run.html_url,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "updated_at": run.updated_at.isoformat() if run.updated_at else None,
            }

        except GithubException as e:
            logger.error(f"Failed to get workflow run status: {e}")
            raise ValueError(f"Failed to get workflow run status: {str(e)}")

    def commit_multiple_files(
        self,
        repo_full_name: str,
        files: List[Dict[str, str]],
        commit_message: str,
        branch: str = "main",
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Commit multiple files in a single commit using Git data API.

        Args:
            repo_full_name: Full repository name (owner/repo)
            files: List of dicts with 'path' and 'content' keys
            commit_message: Commit message
            branch: Branch name
            max_retries: Maximum number of retries on fast-forward errors

        Returns:
            Dictionary with commit information
        """
        import time
        
        repo = self.get_repository(repo_full_name)
        
        # Create blobs first (these are content-addressed, so reusable across retries)
        tree_elements = []
        for file_info in files:
            encoding = file_info.get("encoding", "utf-8")
            blob = repo.create_git_blob(file_info["content"], encoding)
            tree_elements.append(InputGitTreeElement(
                path=file_info["path"],
                mode="100644",
                type="blob",
                sha=blob.sha,
            ))
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Get the LATEST reference to branch (re-fetch on each retry)
                ref = repo.get_git_ref(f"heads/{branch}")
                base_sha = ref.object.sha
                
                logger.debug(f"Commit attempt {attempt + 1}/{max_retries}, base SHA: {base_sha[:7]}")

                # Get base tree
                base_tree = repo.get_git_tree(base_sha)

                # Create new tree with the pre-created blobs
                new_tree = repo.create_git_tree(tree_elements, base_tree)

                # Check if the tree has actually changed to prevent empty commits
                if new_tree.sha == base_tree.sha:
                    logger.info(f"No changes detected in files for branch {branch}, skipping commit")
                    return {
                        "commit_sha": base_sha,
                        "branch": branch,
                        "files_changed": 0,
                        "message": commit_message,
                        "skipped": True,
                    }

                # Create commit
                parent_commit = repo.get_git_commit(base_sha)
                new_commit = repo.create_git_commit(
                    commit_message,
                    new_tree,
                    [parent_commit],
                )

                # Update reference - this is where fast-forward errors occur
                ref.edit(new_commit.sha)

                logger.info(f"Committed {len(files)} files to {branch}: {new_commit.sha[:7]}")

                return {
                    "commit_sha": new_commit.sha,
                    "branch": branch,
                    "files_changed": len(files),
                    "message": commit_message,
                }

            except GithubException as e:
                last_error = e
                error_msg = e.data.get('message', str(e)) if hasattr(e, 'data') else str(e)
                
                # Check if it's a fast-forward error (branch moved)
                if "Update is not a fast forward" in error_msg or e.status == 422:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"Fast-forward error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        continue
                
                logger.error(f"Failed to commit multiple files (GitHub error): {e}")
                raise ValueError(f"Failed to commit files: {error_msg}")
                
            except Exception as e:
                logger.error(f"Failed to commit multiple files (Internal error): {e}", exc_info=True)
                raise ValueError(f"Internal error during commit: {str(e)}")
        
        # All retries exhausted
        logger.error(f"Failed to commit after {max_retries} attempts")
        raise ValueError(f"Failed to commit files after {max_retries} retries: {last_error}")

    def get_repository_tree(
        self,
        repo_full_name: str,
        branch: str = "main",
        recursive: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get the complete file tree of a repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            branch: Branch name
            recursive: Whether to get tree recursively

        Returns:
            List of tree items with path, type, size, sha
        """
        try:
            repo = self.get_repository(repo_full_name)
            branch_ref = repo.get_branch(branch)
            tree = repo.get_git_tree(branch_ref.commit.sha, recursive=recursive)
            
            return [
                {
                    "path": item.path,
                    "type": item.type,  # 'blob' for files, 'tree' for directories
                    "size": item.size if item.type == "blob" else 0,
                    "sha": item.sha,
                }
                for item in tree.tree
            ]
        except GithubException as e:
            logger.error(f"Failed to get repository tree: {e}")
            raise ValueError(f"Failed to get repository tree: {e.data.get('message', str(e))}")

    def get_file_content_with_sha(
        self,
        repo_full_name: str,
        file_path: str,
        ref: str = "main",
    ) -> Tuple[str, str]:
        """Get file content and SHA from a repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            file_path: Path to the file in the repository
            ref: Branch or commit reference

        Returns:
            Tuple of (content, sha)
        """
        try:
            repo = self.get_repository(repo_full_name)
            contents = repo.get_contents(file_path, ref=ref)

            if isinstance(contents, list):
                raise ValueError(f"Path is a directory: {file_path}")

            return contents.decoded_content.decode("utf-8"), contents.sha

        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"File not found: {file_path}")
            logger.error(f"Failed to get file content: {e}")
            raise

    def list_branches(self, repo_full_name: str) -> List[Dict[str, Any]]:
        """List all branches in a repository.

        Args:
            repo_full_name: Full repository name (owner/repo)

        Returns:
            List of branch information dictionaries
        """
        try:
            repo = self.get_repository(repo_full_name)
            branches = repo.get_branches()
            
            return [
                {
                    "name": branch.name,
                    "sha": branch.commit.sha,
                    "protected": branch.protected,
                }
                for branch in branches
            ]
        except GithubException as e:
            logger.error(f"Failed to list branches: {e}")
            raise ValueError(f"Failed to list branches: {e.data.get('message', str(e))}")

    def get_commits(
        self,
        repo_full_name: str,
        branch: str = "main",
        page: int = 1,
        per_page: int = 20,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get commit history for a repository.

        Args:
            repo_full_name: Full repository name (owner/repo)
            branch: Branch name
            page: Page number (1-indexed)
            per_page: Results per page
            path: Optional file path to filter commits

        Returns:
            Dictionary with commits list and total count
        """
        try:
            repo = self.get_repository(repo_full_name)
            
            # Get commits with optional path filter
            kwargs = {"sha": branch}
            if path:
                kwargs["path"] = path
            
            commits_paginated = repo.get_commits(**kwargs)
            
            # Get the specific page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            commits_list = []
            for i, commit in enumerate(commits_paginated):
                if i < start_idx:
                    continue
                if i >= end_idx:
                    break
                    
                commits_list.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": {
                        "name": commit.commit.author.name,
                        "email": commit.commit.author.email,
                        "date": commit.commit.author.date.isoformat() if commit.commit.author.date else None,
                        "avatar_url": commit.author.avatar_url if commit.author else None,
                    },
                    "timestamp": commit.commit.author.date.isoformat() if commit.commit.author.date else None,
                    "url": commit.html_url,
                    "stats": {
                        "additions": commit.stats.additions if commit.stats else 0,
                        "deletions": commit.stats.deletions if commit.stats else 0,
                        "total": commit.stats.total if commit.stats else 0,
                    },
                })
            
            return {
                "commits": commits_list,
                "total_count": commits_paginated.totalCount,
            }
        except GithubException as e:
            logger.error(f"Failed to get commits: {e}")
            raise ValueError(f"Failed to get commits: {e.data.get('message', str(e))}")

    @staticmethod
    def slugify(name: str) -> str:
        """Convert a name to a valid GitHub repository name.

        Args:
            name: Name to convert

        Returns:
            Valid repository name slug
        """
        # Convert to lowercase
        slug = name.lower()
        # Replace spaces and underscores with hyphens
        slug = re.sub(r"[\s_]+", "-", slug)
        # Remove any character that isn't alphanumeric or hyphen
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r"-+", "-", slug)
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        # Limit length
        return slug[:100] if slug else "project"

    def create_repo_secret(
        self,
        repo_full_name: str,
        secret_name: str,
        secret_value: str,
    ) -> Dict[str, Any]:
        """Create or update a repository secret.

        Args:
            repo_full_name: Full repository name (owner/repo)
            secret_name: Name of the secret
            secret_value: Value of the secret

        Returns:
            Dictionary with result information
        """
        try:
            # Fetch public key
            url = f"{self.GITHUB_API_URL}/repos/{repo_full_name}/actions/secrets/public-key"
            headers = {
                "Authorization": f"token {self._access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            
            import httpx
            with httpx.Client() as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    raise ValueError(f"Failed to get repo public key: {resp.text}")
                key_data = resp.json()
                public_key_id = key_data["key_id"]
                public_key_str = key_data["key"]

            # Encrypt the secret
            public_key = nacl.public.PublicKey(public_key_str.encode("utf-8"), nacl.encoding.Base64Encoder)
            sealed_box = nacl.public.SealedBox(public_key)
            encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
            encrypted_b64 = nacl.encoding.Base64Encoder.encode(encrypted).decode("utf-8")

            # Create/Update secret
            secret_url = f"{self.GITHUB_API_URL}/repos/{repo_full_name}/actions/secrets/{secret_name}"
            data = {
                "encrypted_value": encrypted_b64,
                "key_id": public_key_id,
            }
            
            with httpx.Client() as client:
                put_resp = client.put(secret_url, headers=headers, json=data)
                
                if put_resp.status_code not in (201, 204):
                    raise ValueError(f"Failed to create secret: {put_resp.text}")
                    
            logger.info(f"Created secret {secret_name} for {repo_full_name}")
            return {"name": secret_name, "status": "created"}

        except Exception as e:
            logger.error(f"Failed to create repo secret: {e}")
            raise ValueError(f"Failed to create repo secret: {str(e)}")


