"""File operations API endpoints for code editor."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session, require_github_token
from app.models.project import Project
from app.models.user import User
from app.services.github import GitHubService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Files"])


# Request/Response Models
class FileUpdateRequest(BaseModel):
    """Request model for updating a file."""
    file_path: str = Field(..., description="Path to the file in the repository")
    content: str = Field(..., description="New file content")
    message: str = Field(default="Update file", description="Commit message")
    sha: Optional[str] = Field(None, description="Current file SHA for conflict detection")
    branch: Optional[str] = Field(None, description="Branch to update (defaults to main)")


class FileChange(BaseModel):
    """Single file change for multi-file commit."""
    path: str
    content: str
    sha: Optional[str] = None


class MultiFileCommitRequest(BaseModel):
    """Request model for committing multiple files."""
    files: List[FileChange]
    message: str
    branch: str = "main"
    create_branch: bool = False
    base_branch: Optional[str] = "main"


class CreateBranchRequest(BaseModel):
    """Request model for creating a new branch."""
    branch_name: str
    base_branch: str = "main"


def build_tree_hierarchy(flat_items: List[Dict]) -> List[Dict]:
    """Convert flat GitHub tree into hierarchical structure."""
    root: Dict[str, Any] = {"children": {}}
    
    for item in flat_items:
        path_parts = item["path"].split("/")
        current = root
        
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                # Leaf node
                if item["type"] == "blob":
                    current["children"][part] = {
                        "path": item["path"],
                        "type": "file",
                        "size": item.get("size", 0),
                        "sha": item.get("sha"),
                    }
                elif item["type"] == "tree":
                    if part not in current["children"]:
                        current["children"][part] = {
                            "path": item["path"],
                            "type": "directory",
                            "children": {},
                        }
            else:
                # Intermediate directory
                if part not in current["children"]:
                    current["children"][part] = {
                        "path": "/".join(path_parts[:i+1]),
                        "type": "directory",
                        "children": {},
                    }
                current = current["children"][part]
    
    return convert_tree_to_list(root["children"])


def convert_tree_to_list(tree_dict: Dict) -> List[Dict]:
    """Convert tree dictionary to list format for frontend."""
    result = []
    # Sort: directories first, then files, both alphabetically
    sorted_items = sorted(
        tree_dict.items(),
        key=lambda x: (0 if x[1].get("type") == "directory" else 1, x[0].lower())
    )
    
    for name, node in sorted_items:
        if node.get("type") == "directory":
            result.append({
                "path": node["path"],
                "type": "directory",
                "children": convert_tree_to_list(node.get("children", {}))
            })
        else:
            result.append({
                "path": node["path"],
                "type": "file",
                "size": node.get("size", 0),
                "sha": node.get("sha"),
            })
    return result


def count_files(tree: List[Dict]) -> int:
    """Count total number of files in tree."""
    count = 0
    for node in tree:
        if node["type"] == "file":
            count += 1
        elif node["type"] == "directory":
            count += count_files(node.get("children", []))
    return count


def calculate_total_size(tree: List[Dict]) -> int:
    """Calculate total size of all files."""
    total = 0
    for node in tree:
        if node["type"] == "file":
            total += node.get("size", 0)
        elif node["type"] == "directory":
            total += calculate_total_size(node.get("children", []))
    return total


@router.get("/{project_id}/files/tree")
async def get_file_tree(
    project_id: int,
    branch: Optional[str] = Query(None, description="Branch name"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """Fetch complete file tree from GitHub repository using Trees API."""
    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    target_branch = branch or project.github_current_branch or "main"
    
    try:
        # Get recursive tree from GitHub
        tree_data = github_service.get_repository_tree(
            repo_full_name=project.github_repo_full_name,
            branch=target_branch,
            recursive=True,
        )
        
        # Build hierarchical structure
        tree = build_tree_hierarchy(tree_data)
        
        return {
            "tree": tree,
            "total_files": count_files(tree),
            "total_size": calculate_total_size(tree),
            "branch": target_branch,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to fetch file tree: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch file tree: {str(e)}")


@router.get("/{project_id}/files/read")
async def read_file(
    project_id: int,
    file_path: str = Query(..., description="Path to file"),
    branch: Optional[str] = Query(None, description="Branch name"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """Read file content from GitHub repository."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    target_branch = branch or project.github_current_branch or "main"
    
    try:
        # Get file content and metadata
        content, sha = github_service.get_file_content_with_sha(
            repo_full_name=project.github_repo_full_name,
            file_path=file_path,
            ref=target_branch,
        )
        
        # Detect language from file extension
        language = detect_language(file_path)
        
        return {
            "file_path": file_path,
            "content": content,
            "sha": sha,
            "language": language,
            "branch": target_branch,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to read file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.put("/{project_id}/files/update")
async def update_file(
    project_id: int,
    request: FileUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """Update file content in GitHub repository."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    branch = request.branch or project.github_current_branch or "main"
    
    try:
        result = github_service.create_or_update_file(
            repo_full_name=project.github_repo_full_name,
            file_path=request.file_path,
            content=request.content,
            commit_message=request.message,
            branch=branch,
        )
        
        logger.info(f"Updated file {request.file_path} in project {project_id}")
        
        return {
            "success": True,
            "file_path": request.file_path,
            "new_sha": result.get("commit_sha"),
            "branch": branch,
            "commit": {
                "sha": result.get("commit_sha"),
                "message": request.message,
            }
        }
    except Exception as e:
        logger.error(f"Failed to update file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")


@router.get("/{project_id}/commits")
async def get_commit_history(
    project_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    branch: Optional[str] = Query(None, description="Branch name"),
    file_path: Optional[str] = Query(None, description="Filter by file path"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """Get commit history for the project."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    target_branch = branch or project.github_current_branch or "main"
    
    try:
        commits_data = github_service.get_commits(
            repo_full_name=project.github_repo_full_name,
            branch=target_branch,
            page=page,
            per_page=per_page,
            path=file_path,
        )
        
        return {
            "commits": commits_data["commits"],
            "total_count": commits_data.get("total_count", len(commits_data["commits"])),
            "page": page,
            "per_page": per_page,
            "branch": target_branch,
        }
    except Exception as e:
        logger.error(f"Failed to fetch commits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch commits: {str(e)}")


@router.post("/{project_id}/commits/multi")
async def commit_multiple_files(
    project_id: int,
    request: MultiFileCommitRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """Commit multiple file changes in a single commit."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    
    try:
        # Create branch if requested
        if request.create_branch:
            github_service.create_branch(
                repo_full_name=project.github_repo_full_name,
                branch_name=request.branch,
                from_branch=request.base_branch or "main",
            )
        
        # Prepare files for commit
        files = [
            {"path": f.path, "content": f.content}
            for f in request.files
        ]
        
        # Commit multiple files
        commit_result = github_service.commit_multiple_files(
            repo_full_name=project.github_repo_full_name,
            files=files,
            commit_message=request.message,
            branch=request.branch,
        )
        
        logger.info(f"Committed {len(files)} files to project {project_id}")
        
        return {
            "success": True,
            "commit": {
                "sha": commit_result.get("commit_sha"),
                "message": request.message,
                "files_changed": len(files),
            },
            "branch": request.branch,
            "files_changed": len(files),
        }
    except Exception as e:
        logger.error(f"Failed to commit files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to commit files: {str(e)}")


@router.get("/{project_id}/branches")
async def list_branches(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """List all branches in the repository."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    
    try:
        branches = github_service.list_branches(project.github_repo_full_name)
        return {
            "branches": branches,
            "default_branch": project.github_current_branch or "main",
        }
    except Exception as e:
        logger.error(f"Failed to list branches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/branches")
async def create_branch(
    project_id: int,
    request: CreateBranchRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """Create a new branch from base branch."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    github_service = GitHubService(github_token)
    
    try:
        branch_result = github_service.create_branch(
            repo_full_name=project.github_repo_full_name,
            branch_name=request.branch_name,
            from_branch=request.base_branch,
        )
        return {"success": True, "branch": branch_result}
    except Exception as e:
        logger.error(f"Failed to create branch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    import os
    extension_map = {
        ".dart": "dart",
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".html": "html",
        ".css": "css",
        ".scss": "scss",
        ".xml": "xml",
        ".sh": "shell",
        ".gradle": "groovy",
        ".kt": "kotlin",
        ".swift": "swift",
    }
    
    ext = os.path.splitext(file_path)[1].lower()
    return extension_map.get(ext, "plaintext")
