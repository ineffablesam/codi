"""API routes for environment variable management."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.database import get_db_session
from app.models.environment_variable import EnvironmentVariable
from app.models.project import Project
from app.models.user import User
from app.schemas.environment import (
    EnvironmentSyncRequest,
    EnvironmentSyncResponse,
    EnvironmentVariableCreate,
    EnvironmentVariableListResponse,
    EnvironmentVariableResponse,
    EnvironmentVariableUpdate,
)
from app.services.domain.environment import EnvironmentService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["Environment"])


async def _get_user_project(
    project_id: int,
    user_id: int,
    session: AsyncSession,
) -> Project:
    """Get project and verify user ownership.
    
    Args:
        project_id: Project ID
        user_id: User ID  
        session: Database session
        
    Returns:
        Project instance
        
    Raises:
        HTTPException: If project not found or not owned by user
    """
    result = await session.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    
    return project


@router.get("/{project_id}/environment", response_model=EnvironmentVariableListResponse)
async def list_environment_variables(
    project_id: int,
    context: Optional[str] = Query(None, description="Filter by context"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EnvironmentVariableListResponse:
    """List all environment variables for a project.
    
    Args:
        project_id: Project ID
        context: Optional context filter
        session: Database session
        current_user: Authenticated user
        
    Returns:
        List of environment variables
    """
    # Verify project ownership
    await _get_user_project(project_id, current_user.id, session)
    
    # Build query
    query = select(EnvironmentVariable).where(
        EnvironmentVariable.project_id == project_id
    )
    
    if context:
        query = query.where(EnvironmentVariable.context == context)
    
    query = query.order_by(EnvironmentVariable.context, EnvironmentVariable.key)
    
    result = await session.execute(query)
    variables = result.scalars().all()
    
    return EnvironmentVariableListResponse(
        variables=[EnvironmentVariableResponse.model_validate(v) for v in variables],
        total=len(variables),
    )


@router.post("/{project_id}/environment", response_model=EnvironmentVariableResponse, status_code=status.HTTP_201_CREATED)
async def create_environment_variable(
    project_id: int,
    var_data: EnvironmentVariableCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EnvironmentVariableResponse:
    """Create a new environment variable.
    
    Args:
        project_id: Project ID
        var_data: Environment variable data
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Created environment variable
    """
    # Verify project ownership
    await _get_user_project(project_id, current_user.id, session)
    
    # Check if variable with same key already exists
    existing = await session.execute(
        select(EnvironmentVariable).where(
            EnvironmentVariable.project_id == project_id,
            EnvironmentVariable.key == var_data.key,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Environment variable '{var_data.key}' already exists",
        )
    
    # Create new environment variable
    env_var = EnvironmentVariable(
        project_id=project_id,
        key=var_data.key,
        context=var_data.context,
        description=var_data.description,
    )
    env_var.set_value(var_data.value, is_secret=var_data.is_secret)
    
    session.add(env_var)
    await session.commit()
    await session.refresh(env_var)
    
    logger.info(
        f"Created environment variable",
        project_id=project_id,
        key=var_data.key,
        context=var_data.context,
    )
    
    return EnvironmentVariableResponse.model_validate(env_var)


@router.patch("/{project_id}/environment/{var_id}", response_model=EnvironmentVariableResponse)
async def update_environment_variable(
    project_id: int,
    var_id: int,
    var_data: EnvironmentVariableUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EnvironmentVariableResponse:
    """Update an environment variable.
    
    Args:
        project_id: Project ID
        var_id: Environment variable ID
        var_data: Update data
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Updated environment variable
    """
    # Verify project ownership
    await _get_user_project(project_id, current_user.id, session)
    
    # Get environment variable
    result = await session.execute(
        select(EnvironmentVariable).where(
            EnvironmentVariable.id == var_id,
            EnvironmentVariable.project_id == project_id,
        )
    )
    env_var = result.scalar_one_or_none()
    
    if not env_var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment variable not found",
        )
    
    # Update fields
    update_data = var_data.model_dump(exclude_unset=True)
    
    if "value" in update_data:
        # If value is being updated, re-encrypt if needed
        is_secret = update_data.get("is_secret", env_var.is_secret)
        env_var.set_value(update_data["value"], is_secret=is_secret)
        del update_data["value"]
    
    for field, value in update_data.items():
        setattr(env_var, field, value)
    
    await session.commit()
    await session.refresh(env_var)
    
    logger.info(
        f"Updated environment variable",
        project_id=project_id,
        var_id=var_id,
        key=env_var.key,
    )
    
    return EnvironmentVariableResponse.model_validate(env_var)


@router.delete("/{project_id}/environment/{var_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment_variable(
    project_id: int,
    var_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an environment variable.
    
    Args:
        project_id: Project ID
        var_id: Environment variable ID
        session: Database session
        current_user: Authenticated user
    """
    # Verify project ownership
    await _get_user_project(project_id, current_user.id, session)
    
    # Get environment variable
    result = await session.execute(
        select(EnvironmentVariable).where(
            EnvironmentVariable.id == var_id,
            EnvironmentVariable.project_id == project_id,
        )
    )
    env_var = result.scalar_one_or_none()
    
    if not env_var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment variable not found",
        )
    
    await session.delete(env_var)
    await session.commit()
    
    logger.info(
        f"Deleted environment variable",
        project_id=project_id,
        var_id=var_id,
        key=env_var.key,
    )


@router.post("/{project_id}/environment/sync", response_model=EnvironmentSyncResponse)
async def sync_environment_variables(
    project_id: int,
    sync_request: EnvironmentSyncRequest = EnvironmentSyncRequest(),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EnvironmentSyncResponse:
    """Sync environment variables to project's .env file.
    
    Args:
        project_id: Project ID
        sync_request: Sync configuration
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Sync result
    """
    # Verify project ownership
    project = await _get_user_project(project_id, current_user.id, session)
    
    # Get environment variables
    query = select(EnvironmentVariable).where(
        EnvironmentVariable.project_id == project_id
    )
    
    if sync_request.context:
        query = query.where(EnvironmentVariable.context == sync_request.context)
    
    result = await session.execute(query)
    variables = result.scalars().all()
    
    if not variables:
        return EnvironmentSyncResponse(
            success=True,
            message="No environment variables to sync",
            synced_count=0,
            file_path="",
        )
    
    # Sync to file
    try:
        file_path = EnvironmentService.sync_to_file(
            project=project,
            variables=list(variables),
            context=sync_request.context,
            include_secrets=sync_request.include_secrets,
        )
        
        return EnvironmentSyncResponse(
            success=True,
            message=f"Successfully synced {len(variables)} environment variables",
            synced_count=len(variables),
            file_path=file_path,
        )
    except Exception as e:
        logger.error(f"Failed to sync environment variables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync environment variables: {str(e)}",
        )


@router.post("/{project_id}/environment/ensure-defaults", response_model=EnvironmentVariableListResponse)
async def ensure_default_variables(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> EnvironmentVariableListResponse:
    """Ensure default environment variables exist for the project.
    
    This is useful for Serverpod projects that require specific environment variables.
    
    Args:
        project_id: Project ID
        session: Database session
        current_user: Authenticated user
        
    Returns:
        List of all environment variables (including newly created defaults)
    """
    # Verify project ownership
    project = await _get_user_project(project_id, current_user.id, session)
    
    # Get existing variables
    result = await session.execute(
        select(EnvironmentVariable).where(
            EnvironmentVariable.project_id == project_id
        )
    )
    existing_vars = list(result.scalars().all())
    
    # Ensure defaults
    new_vars = EnvironmentService.ensure_defaults(project, existing_vars)
    
    if new_vars:
        for var in new_vars:
            session.add(var)
        await session.commit()
        
        logger.info(
            f"Created {len(new_vars)} default environment variables for project {project_id}"
        )
    
    # Return all variables
    result = await session.execute(
        select(EnvironmentVariable).where(
            EnvironmentVariable.project_id == project_id
        ).order_by(EnvironmentVariable.context, EnvironmentVariable.key)
    )
    all_vars = result.scalars().all()
    
    return EnvironmentVariableListResponse(
        variables=[EnvironmentVariableResponse.model_validate(v) for v in all_vars],
        total=len(all_vars),
    )
