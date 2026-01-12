"""Deployments API endpoints for project deployment management."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_db_session
from app.models.project import Project
from app.models.user import User
from app.models.container import Container, ContainerStatus
from app.models.deployment import Deployment, DeploymentStatus
from app.services.infrastructure.docker import get_docker_service
from app.services.infrastructure.traefik import get_traefik_service
from app.services.domain.framework_detector import detect_framework
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/deployments", tags=["Deployments"])


# Request/Response Models
class DeploymentCreateRequest(BaseModel):
    """Request to create a new deployment."""
    project_id: int
    framework: str = "auto"
    is_preview: bool = False
    branch: str = "main"


class DeploymentResponse(BaseModel):
    """Deployment response model."""
    id: str
    project_id: int
    container_id: Optional[str]
    subdomain: str
    url: str
    status: str
    framework: str
    git_branch: str
    is_preview: bool
    is_production: bool
    created_at: datetime
    deployed_at: Optional[datetime] = None


class DeploymentListResponse(BaseModel):
    """List of deployments response."""
    deployments: List[DeploymentResponse]
    total: int


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
    return project


def _generate_project_slug(project_name: str) -> str:
    """Generate URL-safe project slug."""
    import re
    slug = project_name.lower().strip()
    slug = re.sub(r'[^a-z0-9-]', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug[:50] or "project"


@router.post("", response_model=DeploymentResponse)
async def create_deployment(
    request: DeploymentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DeploymentResponse:
    """Create a new deployment for a project.
    
    This builds the Docker image, creates a container, and sets up routing.
    """
    project = await _get_project_or_404(request.project_id, current_user.id, session)
    
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository")
    
    docker_service = get_docker_service()
    traefik_service = get_traefik_service()
    
    # Generate names
    project_slug = _generate_project_slug(project.name)
    deployment_id = str(uuid.uuid4())
    
    if request.is_preview:
        subdomain = f"{project_slug}-preview-{traefik_service._sanitize_subdomain(request.branch)}"
        container_name = f"codi-{project_slug}-preview-{request.branch}"
        image_tag = f"codi/{project_slug}:{request.branch}"
    else:
        subdomain = project_slug
        container_name = f"codi-{project_slug}"
        image_tag = f"codi/{project_slug}:latest"
    
    # Detect framework
    framework = request.framework
    if framework == "auto":
        detected = detect_framework(project.local_path)
        framework = detected.framework.value
    
    url = traefik_service.get_subdomain_url(project_slug, request.is_preview, request.branch if request.is_preview else None)
    
    # Check for existing deployment with same subdomain and archive it
    existing_deployment_result = await session.execute(
        select(Deployment).where(Deployment.subdomain == subdomain)
    )
    existing_deployment = existing_deployment_result.scalar_one_or_none()
    
    if existing_deployment:
        logger.info(f"Archiving existing deployment {existing_deployment.id} with subdomain {subdomain}")
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        existing_deployment.subdomain = f"archived-{timestamp}-{existing_deployment.subdomain}"
        existing_deployment.status = DeploymentStatus.INACTIVE
        # We don't necessarily stop the container here as the new one will replace it, 
        # but we need to free up the subdomain in the DB.
        session.add(existing_deployment)
        await session.flush()  # Flush to ensure unique constraint check passes for new record
    
    # Create deployment record
    deployment = Deployment(
        id=deployment_id,
        project_id=project.id,
        subdomain=subdomain,
        url=url,
        status=DeploymentStatus.BUILDING,
        framework=framework,
        git_branch=request.branch,
        git_commit_sha=project.git_commit_sha,
        is_preview=request.is_preview,
        is_production=not request.is_preview,
    )
    session.add(deployment)
    await session.commit()
    
    try:
        # Build image
        build_result = await docker_service.build_image(
            project_path=project.local_path,
            image_tag=image_tag,
            framework=framework,
        )
        
        if not build_result.success:
            deployment.status = DeploymentStatus.FAILED
            deployment.status_message = build_result.error
            await session.commit()
            raise HTTPException(status_code=500, detail=f"Build failed: {build_result.error}")
        
        # Stop and remove existing container if any
        existing = await docker_service.get_container(container_name)
        if existing:
            await docker_service.stop_container(container_name)
            await docker_service.remove_container(container_name)
        
        # Get port for framework
        port = traefik_service.get_port_for_framework(framework)
        
        # Generate Traefik labels
        labels = traefik_service.generate_labels(
            project_slug=project_slug,
            container_name=container_name,
            port=port,
            is_preview=request.is_preview,
            branch=request.branch if request.is_preview else None,
        )
        
        deployment.status = DeploymentStatus.DEPLOYING
        await session.commit()
        
        # Create and start container
        container_info = await docker_service.create_container(
            image=image_tag,
            name=container_name,
            labels=labels,
            auto_start=True,
        )
        
        # Save container to database
        container = Container(
            id=container_info.id,
            project_id=project.id,
            name=container_name,
            image=image_tag.split(":")[0],
            image_tag=image_tag.split(":")[-1] if ":" in image_tag else "latest",
            status=ContainerStatus.RUNNING,
            git_branch=request.branch,
            git_commit_sha=project.git_commit_sha,
            port=port,
            is_preview=request.is_preview,
            started_at=datetime.utcnow(),
            build_duration_seconds=int((datetime.utcnow() - deployment.created_at).total_seconds()),
        )
        session.add(container)
        
        # Update deployment
        deployment.container_id = container.id
        deployment.status = DeploymentStatus.ACTIVE
        deployment.deployed_at = datetime.utcnow()
        
        # Update project deployment URL (for production deployments)
        if not request.is_preview:
            project.deployment_url = url
            project.last_deployment_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"Created deployment {deployment_id} for project {project.id} at {url}")
        
        return DeploymentResponse(
            id=deployment.id,
            project_id=deployment.project_id,
            container_id=deployment.container_id,
            subdomain=deployment.subdomain,
            url=deployment.url,
            status=deployment.status.value,
            framework=deployment.framework,
            git_branch=deployment.git_branch,
            is_preview=deployment.is_preview,
            is_production=deployment.is_production,
            created_at=deployment.created_at,
            deployed_at=deployment.deployed_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        deployment.status = DeploymentStatus.FAILED
        deployment.status_message = str(e)
        await session.commit()
        logger.error(f"Deployment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DeploymentResponse:
    """Get deployment details."""
    result = await session.execute(
        select(Deployment).join(Project).where(
            Deployment.id == deployment_id,
            Project.owner_id == current_user.id,
        )
    )
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return DeploymentResponse(
        id=deployment.id,
        project_id=deployment.project_id,
        container_id=deployment.container_id,
        subdomain=deployment.subdomain,
        url=deployment.url,
        status=deployment.status.value,
        framework=deployment.framework,
        git_branch=deployment.git_branch,
        is_preview=deployment.is_preview,
        is_production=deployment.is_production,
        created_at=deployment.created_at,
        deployed_at=deployment.deployed_at,
    )


@router.get("/project/{project_id}", response_model=DeploymentListResponse)
async def list_project_deployments(
    project_id: int,
    include_inactive: bool = Query(False, description="Include inactive deployments"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DeploymentListResponse:
    """List all deployments for a project."""
    project = await _get_project_or_404(project_id, current_user.id, session)
    
    query = select(Deployment).where(Deployment.project_id == project_id)
    
    if not include_inactive:
        query = query.where(Deployment.status.in_([
            DeploymentStatus.ACTIVE,
            DeploymentStatus.BUILDING,
            DeploymentStatus.DEPLOYING,
        ]))
    
    query = query.order_by(Deployment.created_at.desc())
    
    result = await session.execute(query)
    deployments = result.scalars().all()
    
    return DeploymentListResponse(
        deployments=[
            DeploymentResponse(
                id=d.id,
                project_id=d.project_id,
                container_id=d.container_id,
                subdomain=d.subdomain,
                url=d.url,
                status=d.status.value,
                framework=d.framework,
                git_branch=d.git_branch,
                is_preview=d.is_preview,
                is_production=d.is_production,
                created_at=d.created_at,
                deployed_at=d.deployed_at,
            )
            for d in deployments
        ],
        total=len(deployments),
    )


@router.delete("/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a deployment and its container."""
    result = await session.execute(
        select(Deployment).join(Project).where(
            Deployment.id == deployment_id,
            Project.owner_id == current_user.id,
        )
    )
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    docker_service = get_docker_service()
    
    # Remove container if exists
    if deployment.container_id:
        try:
            await docker_service.remove_container(deployment.container_id, force=True)
        except Exception as e:
            logger.warning(f"Failed to remove container: {e}")
    
    deployment.status = DeploymentStatus.DESTROYED
    await session.delete(deployment)
    await session.commit()
    
    return {"success": True, "message": f"Deployment {deployment_id} deleted"}


@router.post("/{deployment_id}/redeploy", response_model=DeploymentResponse)
async def redeploy(
    deployment_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DeploymentResponse:
    """Redeploy an existing deployment with latest code."""
    result = await session.execute(
        select(Deployment).join(Project).where(
            Deployment.id == deployment_id,
            Project.owner_id == current_user.id,
        )
    )
    deployment = result.scalar_one_or_none()
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Create new deployment with same settings
    return await create_deployment(
        DeploymentCreateRequest(
            project_id=deployment.project_id,
            framework=deployment.framework,
            is_preview=deployment.is_preview,
            branch=deployment.git_branch,
        ),
        session=session,
        current_user=current_user,
    )
