"""Projects API endpoints - Local Git version.

All projects are stored locally using GitPython. No external GitHub dependency.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.core.database import get_db_session
from app.models.project import Project, ProjectStatus
from app.models.deployment import Deployment
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithOwner,
)
from app.services.infrastructure.git import LocalGitService, get_git_service
from app.services.domain.starter_template import StarterTemplateService
from app.services.infrastructure.docker import get_docker_service
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


def _project_to_response(p: Project) -> ProjectResponse:
    """Convert a Project model to ProjectResponse schema."""
    return ProjectResponse(
        id=p.id,
        owner_id=p.owner_id,
        name=p.name,
        description=p.description,
        local_path=p.local_path,
        git_commit_sha=p.git_commit_sha,
        git_branch=p.git_branch,
        is_private=p.is_private,
        # Platform configuration
        platform_type=p.platform_type,
        framework=p.framework,
        backend_type=p.backend_type,
        # Status
        status=p.status if isinstance(p.status, str) else p.status.value,
        deployment_url=p.deployment_url,
        deployment_provider=p.deployment_provider,
        last_deployment_at=p.last_deployment_at,
        last_build_status=p.last_build_status,
        last_build_at=p.last_build_at,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum projects to return"),
    status: str = Query("active", description="Filter by status (active, archived, all)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    """List all projects for the current user.

    Args:
        skip: Number of projects to skip (pagination)
        limit: Maximum number of projects to return
        status: Filter by project status
        session: Database session
        current_user: Authenticated user

    Returns:
        List of user's projects
    """
    query = select(Project).where(Project.owner_id == current_user.id)
    
    # Apply status filter
    if status == "active":
        query = query.where(Project.status == ProjectStatus.ACTIVE)
    elif status == "archived":
        query = query.where(Project.status == ProjectStatus.ARCHIVED)
    # if status is "all", no filter applied (except owner)
    
    query = query.order_by(Project.updated_at.desc()).offset(skip).limit(limit)
    
    result = await session.execute(query)
    projects = result.scalars().all()

    # Get total count (with same filter)
    count_query = select(Project.id).where(Project.owner_id == current_user.id)
    if status == "active":
        count_query = count_query.where(Project.status == ProjectStatus.ACTIVE)
    elif status == "archived":
        count_query = count_query.where(Project.status == ProjectStatus.ARCHIVED)
        
    count_result = await session.execute(count_query)
    total = len(count_result.all())

    return ProjectListResponse(
        projects=[_project_to_response(p) for p in projects],
        total=total,
        page=skip // limit + 1,
        per_page=limit,
        pages=(total + limit - 1) // limit if limit > 0 else 1,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Create a new project with local Git repository.

    Args:
        project_data: Project creation data
        session: Database session
        current_user: Authenticated user

    Returns:
        Created project
    """
    # Determine framework - default to flutter for backward compatibility
    framework = getattr(project_data, 'framework', 'flutter') or 'flutter'
    platform_type = getattr(project_data, 'platform_type', 'mobile') or 'mobile'
    backend_type = getattr(project_data, 'backend_type', None)

    # Create local Git repository
    git_service = get_git_service()
    project_slug = LocalGitService.slugify(project_data.name)
    
    try:
        # Initialize the local repository
        project_path = git_service.init_repository(
            project_slug=project_slug,
            user_id=current_user.id,
        )
        
        # Use StarterTemplateService to populate the repository
        template_service = StarterTemplateService(framework=framework)
        await template_service.push_template_to_repo(
            project_path=str(project_path),
            project_name=project_data.name,
        )
        
        # Get the current commit SHA
        git_service.open_repository(str(project_path))
        current_commit = git_service.get_current_commit()
        
        logger.info(f"Created local repository at {project_path}")

    except Exception as e:
        logger.error(f"Failed to create local repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create local repository: {str(e)}",
        )

    # Create project in database
    project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        # Local Git repository
        local_path=str(project_path),
        git_commit_sha=current_commit,
        git_branch="main",
        is_private=project_data.is_private,
        # Multi-platform fields
        platform_type=platform_type,
        framework=framework,
        backend_type=backend_type,
        # Status
        status=ProjectStatus.ACTIVE,
    )

    session.add(project)
    await session.commit()
    await session.refresh(project)

    logger.info(
        f"Project created",
        project_id=project.id,
        local_path=str(project_path),
        user_id=current_user.id,
    )

    # Auto-trigger agent workflow if app_idea is provided
    if getattr(project_data, 'app_idea', None):
        try:
            from app.tasks.celery_app import run_agent_workflow_task
            from app.models.agent_task import AgentTask
            
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            
            # Persist the task in the database
            agent_task = AgentTask(
                id=task_id,
                project_id=project.id,
                user_id=current_user.id,
                status="queued",
                message=f"Build this app: {project_data.app_idea}",
            )
            session.add(agent_task)
            await session.commit()
            
            # Queue the Celery task
            run_agent_workflow_task.delay(
                task_id=task_id,
                project_id=project.id,
                user_id=current_user.id,
                user_message=f"Build this app: {project_data.app_idea}",
                project_folder=str(project_path),
            )
            
            logger.info(
                f"Agent workflow triggered for app idea",
                task_id=task_id,
                project_id=project.id,
            )
        except Exception as e:
            logger.error(f"Failed to trigger agent workflow: {e}")
            # Don't fail the project creation if agent trigger fails

    return _project_to_response(project)



@router.get("/{project_id}", response_model=ProjectWithOwner)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectWithOwner:
    """Get a specific project by ID.

    Args:
        project_id: Project ID
        session: Database session
        current_user: Authenticated user

    Returns:
        Project with owner information
    """
    result = await session.execute(
        select(Project)
        .options(selectinload(Project.owner))
        .where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectWithOwner(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        local_path=project.local_path,
        git_commit_sha=project.git_commit_sha,
        git_branch=project.git_branch,
        is_private=project.is_private,
        platform_type=project.platform_type,
        framework=project.framework,
        backend_type=project.backend_type,
        status=project.status if isinstance(project.status, str) else project.status.value,
        deployment_url=project.deployment_url,
        deployment_provider=project.deployment_provider,
        last_deployment_at=project.last_deployment_at,
        last_build_status=project.last_build_status,
        last_build_at=project.last_build_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner_username=project.owner.github_username or project.owner.email or "Unknown",
        owner_avatar_url=project.owner.github_avatar_url,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Update a project.

    Args:
        project_id: Project ID
        project_data: Update data
        session: Database session
        current_user: Authenticated user

    Returns:
        Updated project
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update fields
    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    project.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(project)

    return _project_to_response(project)


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Archive a project (soft delete).
    
    Archived projects are hidden from the default list but can be restored.
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    project.status = ProjectStatus.ARCHIVED
    project.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(project)
    
    return _project_to_response(project)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """Restore an archived project."""
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    project.status = ProjectStatus.ACTIVE
    project.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(project)
    
    return _project_to_response(project)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a project (hard delete).

    Removes:
    - Database record (and cascading deployments/containers)
    - Local Git repository
    - Running Docker containers
    
    Args:
        project_id: Project ID
        session: Database session
        current_user: Authenticated user
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
        
    # Cleanup Docker containers
    try:
        docker_service = get_docker_service()
        deployments_result = await session.execute(
            select(Deployment).where(Deployment.project_id == project_id)
        )
        deployments = deployments_result.scalars().all()
        
        for deployment in deployments:
            if deployment.container_id:
                try:
                    await docker_service.remove_container(deployment.container_id, force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove container {deployment.container_id}: {e}")
    except Exception as e:
        logger.warning(f"Failed to cleanup containers for project {project_id}: {e}")

    # Remove local repository
    local_path = project.local_path
    if local_path and os.path.exists(local_path):
        try:
            shutil.rmtree(local_path)
            logger.info(f"Removed local repository at {local_path}")
        except Exception as e:
            logger.error(f"Failed to remove local repository at {local_path}: {e}")
            # we continue to delete the DB record even if file deletion fails
            pass

    # Delete from database
    await session.delete(project)
    await session.commit()

    logger.info(f"Project deleted", project_id=project_id, user_id=current_user.id)


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: int,
    path: str = Query("", description="Directory path to list"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List files in the project repository.

    Args:
        project_id: Project ID
        path: Directory path to list
        session: Database session
        current_user: Authenticated user

    Returns:
        List of files and directories
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.local_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no local repository",
        )

    git_service = get_git_service(project.local_path)

    try:
        files = git_service.list_files(path=path)
        return {
            "files": [
                {
                    "path": f.path,
                    "name": f.name,
                    "is_file": f.is_file,
                    "size": f.size,
                }
                for f in files
            ],
            "path": path,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{project_id}/files/{file_path:path}")
async def get_file_content(
    project_id: int,
    file_path: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Get content of a file in the project repository.

    Args:
        project_id: Project ID
        file_path: Path to the file
        session: Database session
        current_user: Authenticated user

    Returns:
        File content
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.local_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no local repository",
        )

    git_service = get_git_service(project.local_path)

    try:
        content = git_service.get_file_content(file_path)
        return {"content": content, "path": file_path}
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{project_id}/branches")
async def list_branches(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all branches in the project repository.

    Args:
        project_id: Project ID
        session: Database session
        current_user: Authenticated user

    Returns:
        List of branches with current branch indicator
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.local_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no local repository",
        )

    git_service = get_git_service(project.local_path)

    try:
        branches = git_service.get_branches()
        current = git_service.get_current_branch()
        return {
            "branches": branches,
            "current": current,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{project_id}/commits")
async def list_commits(
    project_id: int,
    limit: int = Query(20, ge=1, le=100, description="Number of commits to return"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List recent commits in the project repository.

    Args:
        project_id: Project ID
        limit: Number of commits to return
        session: Database session
        current_user: Authenticated user

    Returns:
        List of commits
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not project.local_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no local repository",
        )

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
                    "email": c.email,
                    "timestamp": c.timestamp.isoformat(),
                    "files_changed": c.files_changed,
                }
                for c in commits
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
