"""File operations API endpoints for code editor - Local Git version.

All file operations use local Git repositories. No GitHub API dependency.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import os

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db_session
from app.models.project import Project
from app.models.user import User
from app.services.git_service import get_git_service
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Files"])


# Request/Response Models
class FileUpdateRequest(BaseModel):
    """Request model for updating a file."""
    file_path: str = Field(..., description="Path to the file in the repository")
    content: str = Field(..., description="New file content")
    message: str = Field(default="Update file", description="Commit message")


class FileChange(BaseModel):
    """Single file change for multi-file commit."""
    path: str
    content: str


class MultiFileCommitRequest(BaseModel):
    """Request model for committing multiple files."""
    files: List[FileChange]
    message: str
    branch: str = "main"
    create_branch: bool = False


class CreateBranchRequest(BaseModel):
    """Request model for creating a new branch."""
    branch_name: str
    base_ref: str = "HEAD"


def build_tree_from_local(files: List[Dict]) -> List[Dict]:
    """Convert flat file list into hierarchical tree structure."""
    root: Dict[str, Any] = {"children": {}}
    
    for file_info in files:
        path_parts = file_info["path"].split("/")
        current = root
        
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:
                # Leaf node (file or empty dir)
                if file_info["is_file"]:
                    current["children"][part] = {
                        "path": file_info["path"],
                        "type": "file",
                        "size": file_info.get("size", 0),
                    }
                else:
                    if part not in current["children"]:
                        current["children"][part] = {
                            "path": file_info["path"],
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


async def _get_project_or_404(project_id: int, user_id: int, session: AsyncSession) -> Project:
    """Get project or raise 404."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository")
    return project


@router.get("/{project_id}/files/tree")
async def get_file_tree(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fetch complete file tree from local repository."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        # Get all files recursively
        all_files = git_service.list_all_files()
        
        # Build file info list
        file_infos = []
        for file_path in all_files:
            full_path = os.path.join(project.local_path, file_path)
            file_infos.append({
                "path": file_path,
                "is_file": True,
                "size": os.path.getsize(full_path) if os.path.exists(full_path) else 0,
            })
        
        # Build hierarchical structure
        tree = build_tree_from_local(file_infos)
        
        return {
            "tree": tree,
            "total_files": count_files(tree),
            "total_size": calculate_total_size(tree),
            "branch": project.git_branch,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to fetch file tree: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch file tree: {str(e)}")


@router.get("/{project_id}/files/read")
async def read_file(
    project_id: int,
    file_path: str = Query(..., description="Path to file"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Read file content from local repository."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        content = git_service.get_file_content(file_path)
        language = detect_language(file_path)
        
        return {
            "file_path": file_path,
            "content": content,
            "language": language,
            "branch": project.git_branch,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Failed to read file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@router.put("/{project_id}/files/update")
async def update_file(
    project_id: int,
    request: FileUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update file content in local repository and commit."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        # Write file
        git_service.write_file(request.file_path, request.content)
        
        # Commit change
        commit_info = git_service.commit(
            message=request.message,
            files=[request.file_path],
        )
        
        # Update project commit SHA
        project.git_commit_sha = commit_info.sha
        await session.commit()
        
        logger.info(f"Updated file {request.file_path} in project {project_id}")
        
        return {
            "success": True,
            "file_path": request.file_path,
            "commit": {
                "sha": commit_info.short_sha,
                "message": request.message,
            },
            "branch": project.git_branch,
        }
    except Exception as e:
        logger.error(f"Failed to update file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")


@router.get("/{project_id}/commits")
async def get_commit_history(
    project_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of commits"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get commit history for the project."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        commits = git_service.get_log(n=limit)
        
        return {
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
            "branch": project.git_branch,
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
) -> Dict[str, Any]:
    """Commit multiple file changes in a single commit."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        # Create branch if requested
        if request.create_branch:
            git_service.create_branch(request.branch)
            git_service.checkout(request.branch)
            project.git_branch = request.branch
        
        # Write all files
        file_paths = []
        for file_change in request.files:
            git_service.write_file(file_change.path, file_change.content)
            file_paths.append(file_change.path)
        
        # Commit all files
        commit_info = git_service.commit(
            message=request.message,
            files=file_paths,
        )
        
        # Update project commit SHA
        project.git_commit_sha = commit_info.sha
        await session.commit()
        
        logger.info(f"Committed {len(file_paths)} files to project {project_id}")
        
        return {
            "success": True,
            "commit": {
                "sha": commit_info.short_sha,
                "message": request.message,
                "files_changed": len(file_paths),
            },
            "branch": project.git_branch,
        }
    except Exception as e:
        logger.error(f"Failed to commit files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to commit files: {str(e)}")


@router.get("/{project_id}/branches")
async def list_branches(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all branches in the repository."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        branches = git_service.get_branches()
        current = git_service.get_current_branch()
        return {
            "branches": branches,
            "current_branch": current,
            "default_branch": project.git_branch,
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
) -> Dict[str, Any]:
    """Create a new branch."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        branch_name = git_service.create_branch(request.branch_name, request.base_ref)
        return {"success": True, "branch": branch_name}
    except Exception as e:
        logger.error(f"Failed to create branch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/branches/checkout")
async def checkout_branch(
    project_id: int,
    branch: str = Query(..., description="Branch name to checkout"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Checkout a branch."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    git_service = get_git_service(project.local_path)
    
    try:
        commit_sha = git_service.checkout(branch)
        
        # Update project branch
        project.git_branch = branch
        project.git_commit_sha = commit_sha
        await session.commit()
        
        return {
            "success": True,
            "branch": branch,
            "commit_sha": commit_sha,
        }
    except Exception as e:
        logger.error(f"Failed to checkout branch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
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
