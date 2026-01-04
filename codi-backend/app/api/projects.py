"""Projects API endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_github_token
from app.database import get_db_session
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithOwner,
)
from app.services.github import GitHubService
from app.services.starter_template import StarterTemplateService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum projects to return"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectListResponse:
    """List all projects for the current user.

    Args:
        skip: Number of projects to skip (pagination)
        limit: Maximum number of projects to return
        session: Database session
        current_user: Authenticated user

    Returns:
        List of user's projects
    """
    result = await session.execute(
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    projects = result.scalars().all()

    # Get total count
    count_result = await session.execute(
        select(Project.id).where(Project.owner_id == current_user.id)
    )
    total = len(count_result.all())

    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=p.id,
                owner_id=p.owner_id,
                name=p.name,
                description=p.description,
                github_repo_name=p.github_repo_name,
                github_repo_full_name=p.github_repo_full_name,
                github_repo_url=p.github_repo_url,
                github_clone_url=p.github_clone_url,
                github_default_branch=p.github_default_branch,
                github_current_branch=p.github_current_branch,
                is_private=p.is_private,
                # Platform configuration
                platform_type=p.platform_type,
                framework=p.framework,
                backend_type=p.backend_type,
                deployment_platform=p.deployment_platform,
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
            for p in projects
        ],
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
    github_token: str = Depends(require_github_token),
) -> ProjectResponse:
    """Create a new project with GitHub repository.

    Args:
        project_data: Project creation data
        session: Database session
        current_user: Authenticated user
        github_token: Decrypted GitHub access token

    Returns:
        Created project
    """
    # Create GitHub repository
    github_service = GitHubService(access_token=github_token)
    
    # Determine framework - default to flutter for backward compatibility
    framework = getattr(project_data, 'framework', 'flutter') or 'flutter'
    platform_type = getattr(project_data, 'platform_type', 'mobile') or 'mobile'
    deployment_platform = getattr(project_data, 'deployment_platform', None)
    backend_type = getattr(project_data, 'backend_type', None)
    vercel_config = {}
    vercel_token = None

    # If Vercel is selected, try to get stored OAuth token
    if deployment_platform == "vercel":
        try:
            from app.models.backend_connection import BackendConnection
            result = await session.execute(
                select(BackendConnection).where(
                    BackendConnection.user_id == current_user.id,
                    BackendConnection.provider == "vercel"
                )
            )
            connection = result.scalar_one_or_none()
            if connection:
                vercel_token = connection.get_access_token()
                if vercel_token:
                    vercel_config["VERCEL_TOKEN"] = vercel_token
                    if connection.organization_id:
                        vercel_config["VERCEL_ORG_ID"] = connection.organization_id
                    logger.info("Using stored Vercel OAuth token")
        except Exception as e:
            logger.warning(f"Failed to fetch Vercel connection: {e}")
            
        if not vercel_config.get("VERCEL_TOKEN"):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vercel account not connected. Please connect your Vercel account in settings before deploying.",
            )

    try:
        repo_name = GitHubService.slugify(project_data.name)
        
        # Framework-specific description
        framework_desc = {
            "flutter": "Flutter app",
            "react": "React app",
            "nextjs": "Next.js app",
            "react_native": "React Native app",
        }.get(framework, "App")
        
        repo_info = github_service.create_repository(
            name=repo_name,
            description=project_data.description or f"{framework_desc}: {project_data.name}",
            private=project_data.is_private,
            auto_init=True,
        )

        repo_full_name = repo_info["full_name"]
        repo_url = repo_info["html_url"]
        default_branch = repo_info.get("default_branch", "main")

    except Exception as e:
        logger.error(f"Failed to create GitHub repository: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create GitHub repository: {str(e)}",
        )

    # Create Vercel project if deploying to Vercel
    if deployment_platform == "vercel" and vercel_token:
        try:
            from app.services.vercel import VercelService
            vercel_project = await VercelService.create_project(
                access_token=vercel_token,
                project_name=repo_name,
                github_repo=repo_full_name,
                team_id=vercel_config.get("VERCEL_ORG_ID"),
                framework=framework,
            )
            vercel_config["VERCEL_PROJECT_ID"] = vercel_project["id"]
            logger.info(f"Created Vercel project: {vercel_project['name']} (ID: {vercel_project['id']})")
        except Exception as e:
            logger.error(f"Failed to create Vercel project: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create Vercel project: {str(e)}. Please try again.",
            )

    # Push starter template and enable Pages
    deployment_url = None
    try:
        # Use framework-specific template service
        template_service = StarterTemplateService(
            github_service=github_service,
            framework=framework,
            deployment_platform=deployment_platform or "github_pages",
        )
        await template_service.push_template_to_repo(
            repo_full_name=repo_full_name,
            project_name=repo_name,
            project_title=project_data.name,
            branch=default_branch,
            vercel_config=vercel_config,
        )
        
        # Enable GitHub Pages (required for the deployment workflow)
        pages_info = await github_service.enable_pages(repo_full_name)
        deployment_url = pages_info.get("deployment_url")
        
        # Auto-configure webhook for build notifications
        from app.config import settings
        webhook_url = f"{settings.api_base_url}/api/v1/webhooks/github"
        await github_service.create_webhook(
            repo_full_name=repo_full_name,
            webhook_url=webhook_url,
            secret=settings.github_webhook_secret if settings.github_webhook_secret else None,
            events=["workflow_run", "deployment_status", "push"],
        )
        logger.info(f"Configured webhook for {repo_full_name}")
        
    except Exception as e:
        logger.error(f"Failed to setup repository: {e}")
        # Continue anyway - repo exists

    # Create project in database with platform configuration
    project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        github_repo_name=repo_name,
        github_repo_full_name=repo_full_name,
        github_repo_url=repo_url,
        github_current_branch=default_branch,
        is_private=project_data.is_private,
        # Multi-platform fields
        platform_type=platform_type,
        framework=framework,
        backend_type=backend_type,
        deployment_platform=deployment_platform or ("github_pages" if deployment_url else None),
        # Status
        status=ProjectStatus.ACTIVE,
        deployment_url=deployment_url,
        deployment_provider=deployment_platform or ("github_pages" if deployment_url else None),
    )

    session.add(project)
    await session.commit()
    await session.refresh(project)

    logger.info(
        f"Project created",
        project_id=project.id,
        repo=repo_full_name,
        user_id=current_user.id,
    )

    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        github_repo_name=project.github_repo_name,
        github_repo_full_name=project.github_repo_full_name,
        github_repo_url=project.github_repo_url,
        github_clone_url=project.github_clone_url,
        github_default_branch=project.github_default_branch,
        github_current_branch=project.github_current_branch,
        is_private=project.is_private,
        # Platform configuration
        platform_type=project.platform_type,
        framework=project.framework,
        backend_type=project.backend_type,
        deployment_platform=project.deployment_platform,
        # Status
        status=project.status if isinstance(project.status, str) else project.status.value,
        deployment_url=project.deployment_url,
        deployment_provider=project.deployment_provider,
        last_deployment_at=project.last_deployment_at,
        last_build_status=project.last_build_status,
        last_build_at=project.last_build_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


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
        github_repo_name=project.github_repo_name,
        github_repo_full_name=project.github_repo_full_name,
        github_repo_url=project.github_repo_url,
        github_clone_url=project.github_clone_url,
        github_default_branch=project.github_default_branch,
        github_current_branch=project.github_current_branch,
        is_private=project.is_private,
        status=project.status if isinstance(project.status, str) else project.status.value,
        deployment_url=project.deployment_url,
        deployment_provider=project.deployment_provider,
        last_deployment_at=project.last_deployment_at,
        last_build_status=project.last_build_status,
        last_build_at=project.last_build_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        owner_username=project.owner.github_username,
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

    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        github_repo_name=project.github_repo_name,
        github_repo_full_name=project.github_repo_full_name,
        github_repo_url=project.github_repo_url,
        github_clone_url=project.github_clone_url,
        github_default_branch=project.github_default_branch,
        github_current_branch=project.github_current_branch,
        is_private=project.is_private,
        status=project.status if isinstance(project.status, str) else project.status.value,
        deployment_url=project.deployment_url,
        deployment_provider=project.deployment_provider,
        last_deployment_at=project.last_deployment_at,
        last_build_status=project.last_build_status,
        last_build_at=project.last_build_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a project (soft delete by setting status to archived).

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

    # Soft delete
    project.status = ProjectStatus.ARCHIVED
    project.updated_at = datetime.now(timezone.utc)
    await session.commit()

    logger.info(f"Project archived", project_id=project_id, user_id=current_user.id)


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: int,
    path: str = Query("", description="Directory path to list"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    github_token: str = Depends(require_github_token),
) -> Dict[str, Any]:
    """List files in the project repository.

    Args:
        project_id: Project ID
        path: Directory path to list
        session: Database session
        current_user: Authenticated user
        github_token: GitHub access token

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

    if not project.github_repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no linked repository",
        )

    github_service = GitHubService(access_token=github_token)

    try:
        files = github_service.list_files(
            repo_full_name=project.github_repo_full_name,
            path=path,
            ref=project.github_current_branch or "main",
        )
        return {"files": files, "path": path}
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
    github_token: str = Depends(require_github_token),
) -> Dict[str, str]:
    """Get content of a file in the project repository.

    Args:
        project_id: Project ID
        file_path: Path to the file
        session: Database session
        current_user: Authenticated user
        github_token: GitHub access token

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

    if not project.github_repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no linked repository",
        )

    github_service = GitHubService(access_token=github_token)

    try:
        content = github_service.get_file_content(
            repo_full_name=project.github_repo_full_name,
            file_path=file_path,
            ref=project.github_current_branch or "main",
        )
        return {"content": content, "path": file_path}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
