"""Containers API endpoints for Docker container management."""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_db_session
from app.models.project import Project
from app.models.user import User
from app.models.container import Container, ContainerStatus
from app.services.infrastructure.docker import get_docker_service
from app.services.infrastructure.traefik import get_traefik_service
from app.services.domain.framework_detector import detect_framework
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/containers", tags=["Containers"])


# Request/Response Models
class ContainerCreateRequest(BaseModel):
    """Request to create a new container."""
    project_id: int
    image_tag: Optional[str] = None
    framework: str = "auto"
    is_preview: bool = False
    branch: str = "main"
    cpu_limit: float = 0.5
    memory_limit_mb: int = 512


class ContainerResponse(BaseModel):
    """Container response model."""
    id: str
    project_id: int
    name: str
    image: str
    status: str
    git_branch: str
    port: int
    is_preview: bool
    url: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None


class ContainerStatsResponse(BaseModel):
    """Container stats response."""
    container_id: str
    cpu_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    memory_percent: float
    network_rx_bytes: int
    network_tx_bytes: int


class ContainerLogsResponse(BaseModel):
    """Container logs response."""
    container_id: str
    logs: List[str]
    line_count: int


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


@router.post("", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerResponse:
    """Create and start a new container for a project."""
    project = await _get_project_or_404(request.project_id, current_user.id, session)
    
    if not project.local_path:
        raise HTTPException(status_code=400, detail="Project has no local repository")
    
    docker_service = get_docker_service()
    traefik_service = get_traefik_service()
    
    # Generate names
    project_slug = _generate_project_slug(project.name)
    
    if request.is_preview:
        container_name = f"codi-{project_slug}-preview-{request.branch}"
    else:
        container_name = f"codi-{project_slug}"
    
    # Detect framework if auto
    framework = request.framework
    if framework == "auto":
        detected = detect_framework(project.local_path)
        framework = detected.framework.value
    
    # Generate image tag
    if request.image_tag:
        image_tag = request.image_tag
    elif request.is_preview:
        image_tag = f"codi/{project_slug}:{request.branch}"
    else:
        image_tag = f"codi/{project_slug}:latest"
    
    try:
        # Build image
        build_result = await docker_service.build_image(
            project_path=project.local_path,
            image_tag=image_tag,
            framework=framework,
        )
        
        if not build_result.success:
            raise HTTPException(status_code=500, detail=f"Build failed: {build_result.error}")
        
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
        
        # Create container
        container_info = await docker_service.create_container(
            image=image_tag,
            name=container_name,
            labels=labels,
            cpu_limit=request.cpu_limit,
            memory_limit=f"{request.memory_limit_mb}m",
            auto_start=True,
        )
        
        # Save to database
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
            cpu_limit=request.cpu_limit,
            memory_limit_mb=request.memory_limit_mb,
            is_preview=request.is_preview,
            started_at=datetime.utcnow(),
        )
        session.add(container)
        await session.commit()
        
        # Get URL
        url = traefik_service.get_subdomain_url(project_slug, request.is_preview, request.branch if request.is_preview else None)
        
        logger.info(f"Created container {container_name} for project {project.id}")
        
        return ContainerResponse(
            id=container.id,
            project_id=container.project_id,
            name=container.name,
            image=image_tag,
            status=container.status.value,
            git_branch=container.git_branch,
            port=container.port,
            is_preview=container.is_preview,
            url=url,
            created_at=container.created_at,
            started_at=container.started_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create container: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}", response_model=ContainerResponse)
async def get_container(
    container_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerResponse:
    """Get container details."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Get current status from Docker
    docker_service = get_docker_service()
    traefik_service = get_traefik_service()
    
    docker_container = await docker_service.get_container(container_id)
    if docker_container:
        container.status = ContainerStatus(docker_container.status.value)
        await session.commit()
    
    # Get URL
    project_slug = container.name.replace("codi-", "").split("-preview-")[0]
    url = traefik_service.get_subdomain_url(
        project_slug,
        container.is_preview,
        container.git_branch if container.is_preview else None,
    )
    
    return ContainerResponse(
        id=container.id,
        project_id=container.project_id,
        name=container.name,
        image=f"{container.image}:{container.image_tag}",
        status=container.status.value,
        git_branch=container.git_branch,
        port=container.port,
        is_preview=container.is_preview,
        url=url,
        created_at=container.created_at,
        started_at=container.started_at,
    )


@router.post("/{container_id}/start", response_model=ContainerResponse)
async def start_container(
    container_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerResponse:
    """Start a stopped container."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = get_docker_service()
    
    try:
        await docker_service.start_container(container_id)
        container.status = ContainerStatus.RUNNING
        container.started_at = datetime.utcnow()
        await session.commit()
        
        return ContainerResponse(
            id=container.id,
            project_id=container.project_id,
            name=container.name,
            image=f"{container.image}:{container.image_tag}",
            status=container.status.value,
            git_branch=container.git_branch,
            port=container.port,
            is_preview=container.is_preview,
            created_at=container.created_at,
            started_at=container.started_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/stop", response_model=ContainerResponse)
async def stop_container(
    container_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerResponse:
    """Stop a running container."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = get_docker_service()
    
    try:
        await docker_service.stop_container(container_id)
        container.status = ContainerStatus.STOPPED
        container.stopped_at = datetime.utcnow()
        await session.commit()
        
        return ContainerResponse(
            id=container.id,
            project_id=container.project_id,
            name=container.name,
            image=f"{container.image}:{container.image_tag}",
            status=container.status.value,
            git_branch=container.git_branch,
            port=container.port,
            is_preview=container.is_preview,
            created_at=container.created_at,
            started_at=container.started_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{container_id}/restart", response_model=ContainerResponse)
async def restart_container(
    container_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerResponse:
    """Restart a container."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = get_docker_service()
    
    try:
        await docker_service.restart_container(container_id)
        container.status = ContainerStatus.RUNNING
        container.started_at = datetime.utcnow()
        await session.commit()
        
        return ContainerResponse(
            id=container.id,
            project_id=container.project_id,
            name=container.name,
            image=f"{container.image}:{container.image_tag}",
            status=container.status.value,
            git_branch=container.git_branch,
            port=container.port,
            is_preview=container.is_preview,
            created_at=container.created_at,
            started_at=container.started_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{container_id}")
async def delete_container(
    container_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a container."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = get_docker_service()
    
    try:
        await docker_service.remove_container(container_id, force=True)
        container.status = ContainerStatus.DESTROYED
        await session.delete(container)
        await session.commit()
        
        return {"success": True, "message": f"Container {container_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}/logs", response_model=ContainerLogsResponse)
async def get_container_logs(
    container_id: str,
    tail: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerLogsResponse:
    """Get container logs."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = get_docker_service()
    
    try:
        logs = await docker_service.get_container_logs(container_id, tail=tail)
        return ContainerLogsResponse(
            container_id=container_id,
            logs=logs,
            line_count=len(logs),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{container_id}/stats", response_model=ContainerStatsResponse)
async def get_container_stats(
    container_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ContainerStatsResponse:
    """Get container resource stats."""
    result = await session.execute(
        select(Container).join(Project).where(
            Container.id == container_id,
            Project.owner_id == current_user.id,
        )
    )
    container = result.scalar_one_or_none()
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    docker_service = get_docker_service()
    
    try:
        stats = await docker_service.get_container_stats(container_id)
        return ContainerStatsResponse(
            container_id=stats.container_id,
            cpu_percent=stats.cpu_percent,
            memory_usage_mb=stats.memory_usage_mb,
            memory_limit_mb=stats.memory_limit_mb,
            memory_percent=stats.memory_percent,
            network_rx_bytes=stats.network_rx_bytes,
            network_tx_bytes=stats.network_tx_bytes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/{container_id}/logs/stream")
async def stream_container_logs(
    websocket: WebSocket,
    container_id: str,
) -> None:
    """WebSocket endpoint for streaming container logs."""
    await websocket.accept()
    
    docker_service = get_docker_service()
    
    try:
        async for log_line in docker_service.stream_logs(container_id):
            await websocket.send_text(log_line)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for container {container_id}")
    except Exception as e:
        logger.error(f"Error streaming logs: {e}")
        await websocket.close(code=1011, reason=str(e))
