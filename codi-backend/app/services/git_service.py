"""Local Git service for repository operations.

Replaces GitHub service with local Git operations using GitPython.
All project repositories are stored locally at /var/codi/repos/.
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import git
from git import Repo, InvalidGitRepositoryError, GitCommandError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Default repos directory - can be configured via settings
REPOS_BASE_PATH = Path(os.getenv("CODI_REPOS_PATH", "/var/codi/repos"))


@dataclass
class FileInfo:
    """Information about a file in the repository."""
    path: str
    name: str
    is_file: bool
    size: Optional[int] = None
    sha: Optional[str] = None


@dataclass
class CommitInfo:
    """Information about a Git commit."""
    sha: str
    short_sha: str
    message: str
    author: str
    email: str
    timestamp: datetime
    files_changed: int


class LocalGitService:
    """Service for local Git repository operations.
    
    Replaces GitHubService - all operations are local, no external API calls.
    """
    
    def __init__(self, project_folder: Optional[str] = None) -> None:
        """Initialize the local Git service.
        
        Args:
            project_folder: Optional path to existing project folder.
        """
        self.project_folder = Path(project_folder) if project_folder else None
        self._repo: Optional[Repo] = None
    
    @staticmethod
    def slugify(name: str) -> str:
        """Convert project name to URL-safe slug.
        
        Args:
            name: Project name
            
        Returns:
            URL-safe slug
        """
        # Convert to lowercase
        slug = name.lower()
        # Replace spaces and underscores with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove non-alphanumeric characters except hyphens
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug or 'project'
    
    @staticmethod
    def get_project_path(project_slug: str, user_id: int) -> Path:
        """Get the full path for a project repository.
        
        Args:
            project_slug: URL-safe project name
            user_id: Owner's user ID
            
        Returns:
            Full path to project directory
        """
        return REPOS_BASE_PATH / str(user_id) / project_slug
    
    @property
    def repo(self) -> Repo:
        """Get the Git repository object (lazy initialization)."""
        if self._repo is None:
            if self.project_folder is None:
                raise ValueError("Project folder not set")
            try:
                self._repo = Repo(self.project_folder)
            except InvalidGitRepositoryError:
                raise ValueError(f"Not a valid Git repository: {self.project_folder}")
        return self._repo
    
    def init_repository(
        self,
        project_slug: str,
        user_id: int,
        initial_files: Optional[Dict[str, str]] = None,
    ) -> Path:
        """Initialize a new Git repository.
        
        Args:
            project_slug: URL-safe project name
            user_id: Owner's user ID
            initial_files: Optional dict of {file_path: content} for initial commit
            
        Returns:
            Path to the created repository
        """
        project_path = self.get_project_path(project_slug, user_id)
        
        # Create directory if it doesn't exist
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git repository
        repo = Repo.init(project_path)
        self._repo = repo
        self.project_folder = project_path
        
        # Create initial files if provided
        if initial_files:
            for file_path, content in initial_files.items():
                full_path = project_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding='utf-8')
            
            # Stage all files
            repo.index.add(list(initial_files.keys()))
            
            # Create initial commit
            repo.index.commit("Initial commit: Project created by Codi")
        else:
            # Create empty README
            readme_path = project_path / "README.md"
            readme_path.write_text(f"# {project_slug}\n\nCreated with Codi.\n")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit: Project created by Codi")
        
        logger.info(f"Created repository at {project_path}")
        return project_path
    
    def clone_repository(self, source_path: str, target_slug: str, user_id: int) -> Path:
        """Clone a repository from another location.
        
        Args:
            source_path: Path to source repository
            target_slug: Target project slug
            user_id: Owner's user ID
            
        Returns:
            Path to cloned repository
        """
        target_path = self.get_project_path(target_slug, user_id)
        
        # Clone the repository
        repo = Repo.clone_from(source_path, target_path)
        self._repo = repo
        self.project_folder = target_path
        
        logger.info(f"Cloned repository from {source_path} to {target_path}")
        return target_path
    
    def open_repository(self, project_path: str) -> "LocalGitService":
        """Open an existing repository.
        
        Args:
            project_path: Path to repository
            
        Returns:
            Self for chaining
        """
        self.project_folder = Path(project_path)
        self._repo = None  # Will be lazy loaded
        return self
    
    def get_file_content(self, file_path: str, ref: str = "HEAD") -> str:
        """Get content of a file from the repository.
        
        Args:
            file_path: Path to file within repository
            ref: Git reference (branch, tag, commit SHA)
            
        Returns:
            File content as string
        """
        try:
            # If ref is HEAD, read from working directory
            if ref == "HEAD":
                full_path = self.project_folder / file_path
                if full_path.exists():
                    return full_path.read_text(encoding='utf-8')
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Otherwise, read from git tree
            tree = self.repo.commit(ref).tree
            blob = tree / file_path
            return blob.data_stream.read().decode('utf-8')
        except (KeyError, FileNotFoundError) as e:
            raise FileNotFoundError(f"File not found: {file_path} at ref {ref}") from e
    
    def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file in the repository.
        
        Args:
            file_path: Path to file within repository
            content: File content
            
        Returns:
            Full path to the written file
        """
        full_path = self.project_folder / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
        logger.debug(f"Wrote file: {file_path}")
        return str(full_path)
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from the repository.
        
        Args:
            file_path: Path to file within repository
            
        Returns:
            True if file was deleted
        """
        full_path = self.project_folder / file_path
        if full_path.exists():
            full_path.unlink()
            logger.debug(f"Deleted file: {file_path}")
            return True
        return False
    
    def list_files(self, path: str = "", ref: str = "HEAD") -> List[FileInfo]:
        """List files in a directory.
        
        Args:
            path: Directory path within repository (empty for root)
            ref: Git reference
            
        Returns:
            List of FileInfo objects
        """
        files: List[FileInfo] = []
        
        # List from working directory
        if ref == "HEAD":
            target_path = self.project_folder / path if path else self.project_folder
            if not target_path.exists():
                return files
            
            for item in target_path.iterdir():
                if item.name.startswith('.git'):
                    continue
                relative_path = str(item.relative_to(self.project_folder))
                files.append(FileInfo(
                    path=relative_path,
                    name=item.name,
                    is_file=item.is_file(),
                    size=item.stat().st_size if item.is_file() else None,
                ))
            return files
        
        # List from specific commit
        try:
            tree = self.repo.commit(ref).tree
            if path:
                tree = tree / path
            
            for item in tree:
                files.append(FileInfo(
                    path=str(Path(path) / item.name) if path else item.name,
                    name=item.name,
                    is_file=item.type == 'blob',
                    size=item.size if item.type == 'blob' else None,
                    sha=item.hexsha,
                ))
        except (KeyError, TypeError):
            pass
        
        return files
    
    def list_all_files(self, include_hidden: bool = False) -> List[str]:
        """Recursively list all files in repository.
        
        Args:
            include_hidden: Include hidden files/directories
            
        Returns:
            List of file paths relative to repository root
        """
        files = []
        for root, dirs, filenames in os.walk(self.project_folder):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                filenames = [f for f in filenames if not f.startswith('.')]
            
            for filename in filenames:
                full_path = Path(root) / filename
                relative_path = full_path.relative_to(self.project_folder)
                files.append(str(relative_path))
        return files
    
    def commit(
        self,
        message: str,
        files: Optional[List[str]] = None,
        all_changes: bool = False,
    ) -> CommitInfo:
        """Create a git commit.
        
        Args:
            message: Commit message
            files: Specific files to commit (None for all staged)
            all_changes: Stage all changes before commit
            
        Returns:
            CommitInfo with commit details
        """
        if all_changes:
            # Stage all changes
            self.repo.git.add('-A')
        elif files:
            # Stage specific files
            self.repo.index.add(files)
        
        # Create commit
        commit = self.repo.index.commit(message)
        
        logger.info(f"Created commit: {commit.hexsha[:7]} - {message}")
        
        return CommitInfo(
            sha=commit.hexsha,
            short_sha=commit.hexsha[:7],
            message=message,
            author=commit.author.name,
            email=commit.author.email,
            timestamp=datetime.fromtimestamp(commit.committed_date),
            files_changed=len(commit.stats.files),
        )
    
    def create_branch(self, branch_name: str, from_ref: str = "HEAD") -> str:
        """Create a new branch.
        
        Args:
            branch_name: Name for the new branch
            from_ref: Reference to create branch from
            
        Returns:
            Name of created branch
        """
        self.repo.create_head(branch_name, commit=from_ref)
        logger.info(f"Created branch: {branch_name} from {from_ref}")
        return branch_name
    
    def checkout(self, ref: str) -> str:
        """Checkout a branch or commit.
        
        Args:
            ref: Branch name or commit SHA
            
        Returns:
            Current HEAD reference
        """
        try:
            # Try as branch first
            self.repo.heads[ref].checkout()
        except (IndexError, AttributeError):
            # Fall back to detached HEAD
            self.repo.git.checkout(ref)
        
        logger.info(f"Checked out: {ref}")
        return str(self.repo.head.commit)
    
    def get_current_branch(self) -> str:
        """Get the current branch name.
        
        Returns:
            Current branch name or 'detached HEAD'
        """
        try:
            return self.repo.active_branch.name
        except TypeError:
            return "detached HEAD"
    
    def get_current_commit(self) -> str:
        """Get the current commit SHA.
        
        Returns:
            Current commit SHA
        """
        return str(self.repo.head.commit)
    
    def get_branches(self) -> List[str]:
        """Get list of all branches.
        
        Returns:
            List of branch names
        """
        return [head.name for head in self.repo.heads]
    
    def get_log(self, n: int = 10, ref: str = "HEAD") -> List[CommitInfo]:
        """Get commit history.
        
        Args:
            n: Number of commits to return
            ref: Reference to start from
            
        Returns:
            List of CommitInfo objects
        """
        commits = []
        for commit in self.repo.iter_commits(ref, max_count=n):
            commits.append(CommitInfo(
                sha=commit.hexsha,
                short_sha=commit.hexsha[:7],
                message=commit.message.strip(),
                author=commit.author.name,
                email=commit.author.email,
                timestamp=datetime.fromtimestamp(commit.committed_date),
                files_changed=len(commit.stats.files),
            ))
        return commits
    
    def get_diff(self, ref1: str = "HEAD~1", ref2: str = "HEAD") -> str:
        """Get diff between two references.
        
        Args:
            ref1: First reference
            ref2: Second reference
            
        Returns:
            Diff as string
        """
        return self.repo.git.diff(ref1, ref2)
    
    def status(self) -> Dict[str, List[str]]:
        """Get repository status.
        
        Returns:
            Dict with 'staged', 'modified', 'untracked' file lists
        """
        return {
            'staged': [item.a_path for item in self.repo.index.diff("HEAD")],
            'modified': [item.a_path for item in self.repo.index.diff(None)],
            'untracked': list(self.repo.untracked_files),
        }
    
    def reset(self, ref: str = "HEAD", hard: bool = False) -> str:
        """Reset to a specific commit.
        
        Args:
            ref: Reference to reset to
            hard: Hard reset (discard changes)
            
        Returns:
            Current commit SHA after reset
        """
        mode = '--hard' if hard else '--mixed'
        self.repo.git.reset(mode, ref)
        logger.info(f"Reset to {ref} ({mode})")
        return str(self.repo.head.commit)
    
    def clean(self, force: bool = True, directories: bool = True) -> None:
        """Remove untracked files.
        
        Args:
            force: Force removal
            directories: Also remove untracked directories
        """
        args = ['-f'] if force else []
        if directories:
            args.append('-d')
        self.repo.git.clean(*args)
        logger.info("Cleaned untracked files")
    
    def delete_repository(self) -> bool:
        """Delete the entire repository directory.
        
        Returns:
            True if deleted successfully
        """
        if self.project_folder and self.project_folder.exists():
            shutil.rmtree(self.project_folder)
            logger.info(f"Deleted repository: {self.project_folder}")
            self._repo = None
            self.project_folder = None
            return True
        return False
    
    def get_file_tree(self, max_depth: int = 3) -> Dict[str, Any]:
        """Get file tree structure for the repository.
        
        Args:
            max_depth: Maximum directory depth to traverse
            
        Returns:
            Nested dictionary representing file tree
        """
        def build_tree(path: Path, current_depth: int) -> Dict[str, Any]:
            result = {}
            if current_depth > max_depth:
                return result
            
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith('.git'):
                        continue
                    if item.is_file():
                        result[item.name] = {
                            'type': 'file',
                            'size': item.stat().st_size,
                        }
                    elif item.is_dir():
                        result[item.name] = {
                            'type': 'directory',
                            'children': build_tree(item, current_depth + 1),
                        }
            except PermissionError:
                pass
            
            return result
        
        return build_tree(self.project_folder, 0)


# Singleton-like access for convenience
_default_service: Optional[LocalGitService] = None


def get_git_service(project_folder: Optional[str] = None) -> LocalGitService:
    """Get a LocalGitService instance.
    
    Args:
        project_folder: Optional path to project folder
        
    Returns:
        LocalGitService instance
    """
    return LocalGitService(project_folder=project_folder)
