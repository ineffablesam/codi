"""Backend OAuth API endpoints for connecting Supabase/Firebase accounts."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.config import settings
from app.database import get_db_session
from app.models.backend_connection import BackendConnection, ProjectBackendConfig
from app.models.project import Project
from app.models.user import User
from app.services.supabase_oauth import SupabaseOAuthService
from app.services.firebase_service import FirebaseOAuthService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/backend", tags=["Backend Integration"])


# ============ Pydantic Models ============

class OAuthStartResponse(BaseModel):
    """Response for starting OAuth flow."""
    authorization_url: str
    state: str
    provider: str


class OAuthCallbackRequest(BaseModel):
    """Request for OAuth callback."""
    code: str
    state: str


class ConnectionStatusResponse(BaseModel):
    """Response for connection status."""
    provider: str
    is_connected: bool
    organization_id: Optional[str] = None
    connected_at: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Organization/project from provider."""
    id: str
    name: str
    provider: str


class ProvisionRequest(BaseModel):
    """Request to provision backend for a project."""
    project_id: int
    provider: str
    organization_id: Optional[str] = None  # For Supabase
    firebase_project_id: Optional[str] = None  # For Firebase (existing project)


class ServerpodConfigRequest(BaseModel):
    """Manual Serverpod configuration."""
    project_id: int
    server_url: str
    api_key: Optional[str] = None


# ============ OAuth Flow Endpoints ============

@router.get("/connect/{provider}", response_model=OAuthStartResponse)
async def start_oauth_flow(
    provider: str,
    current_user: User = Depends(get_current_user),
) -> OAuthStartResponse:
    """Start OAuth flow for a backend provider.

    Generates authorization URL for user to connect their account.

    Args:
        provider: 'supabase' or 'firebase'
    """
    if provider not in ("supabase", "firebase"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider: {provider}",
        )

    # Callback URL
    redirect_uri = f"{settings.api_base_url}/api/v1/backend/callback/{provider}"

    if provider == "supabase":
        service = SupabaseOAuthService()
        result = service.get_authorization_url(redirect_uri)
    else:  # firebase
        service = FirebaseOAuthService()
        result = service.get_authorization_url(redirect_uri)

    # Store state in session/cache (simplified - in production use Redis)
    # For now, we'll pass state back and verify on callback

    return OAuthStartResponse(
        authorization_url=result["authorization_url"],
        state=result["state"],
        provider=provider,
    )


@router.post("/callback/{provider}")
async def oauth_callback(
    provider: str,
    callback_data: OAuthCallbackRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Handle OAuth callback from provider.

    Exchanges code for tokens and saves connection.

    Args:
        provider: 'supabase' or 'firebase'
        callback_data: Authorization code and state
    """
    redirect_uri = f"{settings.api_base_url}/api/v1/backend/callback/{provider}"

    try:
        if provider == "supabase":
            async with SupabaseOAuthService() as service:
                tokens = await service.exchange_code_for_tokens(
                    code=callback_data.code,
                    redirect_uri=redirect_uri,
                )
        elif provider == "firebase":
            # Firebase requires client credentials - these would come from user config
            # For now, we'll use environment variables or user-provided config
            async with FirebaseOAuthService() as service:
                tokens = await service.exchange_code_for_tokens(
                    code=callback_data.code,
                    redirect_uri=redirect_uri,
                    client_id=settings.google_client_id or "",
                    client_secret=settings.google_client_secret or "",
                )
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        # Check for existing connection
        result = await session.execute(
            select(BackendConnection).where(
                BackendConnection.user_id == current_user.id,
                BackendConnection.provider == provider,
            )
        )
        connection = result.scalar_one_or_none()

        if connection:
            # Update existing
            connection.set_access_token(tokens["access_token"])
            if tokens.get("refresh_token"):
                connection.set_refresh_token(tokens["refresh_token"])
            connection.token_expires_at = tokens["expires_at"]
            connection.is_connected = "connected"
            connection.last_error = None
            connection.updated_at = datetime.now(timezone.utc)
        else:
            # Create new
            connection = BackendConnection(
                user_id=current_user.id,
                provider=provider,
                is_connected="connected",
            )
            connection.set_access_token(tokens["access_token"])
            if tokens.get("refresh_token"):
                connection.set_refresh_token(tokens["refresh_token"])
            connection.token_expires_at = tokens["expires_at"]
            session.add(connection)

        await session.commit()

        logger.info(f"User {current_user.id} connected {provider}")

        return {
            "success": True,
            "provider": provider,
            "message": f"Successfully connected to {provider}",
        }

    except Exception as e:
        logger.error(f"OAuth callback failed for {provider}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect: {str(e)}",
        )


@router.get("/status/{provider}", response_model=ConnectionStatusResponse)
async def get_connection_status(
    provider: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ConnectionStatusResponse:
    """Check if user has connected a provider."""
    result = await session.execute(
        select(BackendConnection).where(
            BackendConnection.user_id == current_user.id,
            BackendConnection.provider == provider,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or connection.is_connected != "connected":
        return ConnectionStatusResponse(
            provider=provider,
            is_connected=False,
        )

    return ConnectionStatusResponse(
        provider=provider,
        is_connected=True,
        organization_id=connection.organization_id,
        connected_at=connection.created_at.isoformat() if connection.created_at else None,
    )


@router.delete("/disconnect/{provider}")
async def disconnect_provider(
    provider: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Disconnect a provider account."""
    result = await session.execute(
        select(BackendConnection).where(
            BackendConnection.user_id == current_user.id,
            BackendConnection.provider == provider,
        )
    )
    connection = result.scalar_one_or_none()

    if connection:
        await session.delete(connection)
        await session.commit()

    return {"message": f"Disconnected from {provider}"}


# ============ Organization/Project Listing ============

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    provider: str = Query(..., description="Provider: supabase or firebase"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> List[OrganizationResponse]:
    """List organizations/projects from connected provider."""
    # Get connection
    result = await session.execute(
        select(BackendConnection).where(
            BackendConnection.user_id == current_user.id,
            BackendConnection.provider == provider,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or connection.is_connected != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not connected to {provider}",
        )

    access_token = connection.get_access_token()
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token")

    try:
        if provider == "supabase":
            async with SupabaseOAuthService(access_token) as service:
                orgs = await service.list_organizations()
                return [
                    OrganizationResponse(
                        id=org["id"],
                        name=org.get("name", "Unnamed"),
                        provider="supabase",
                    )
                    for org in orgs
                ]
        elif provider == "firebase":
            async with FirebaseOAuthService(access_token) as service:
                projects = await service.list_projects()
                return [
                    OrganizationResponse(
                        id=p.get("projectId", p.get("name", "").split("/")[-1]),
                        name=p.get("displayName", "Unnamed"),
                        provider="firebase",
                    )
                    for p in projects
                ]
        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")
    except Exception as e:
        logger.error(f"Failed to list organizations: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============ Provisioning ============

@router.post("/provision")
async def provision_backend(
    request: ProvisionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Provision backend resources for a project.

    Creates Supabase project or Firebase web app and stores keys.
    """
    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get connection
    result = await session.execute(
        select(BackendConnection).where(
            BackendConnection.user_id == current_user.id,
            BackendConnection.provider == request.provider,
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or connection.is_connected != "connected":
        raise HTTPException(status_code=400, detail=f"Not connected to {request.provider}")

    access_token = connection.get_access_token()
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token")

    try:
        if request.provider == "supabase":
            if not request.organization_id:
                raise HTTPException(status_code=400, detail="organization_id required for Supabase")

            async with SupabaseOAuthService(access_token) as service:
                result_data = await service.provision_project_for_codi(
                    organization_id=request.organization_id,
                    project_name=project.name,
                )

            # Save config
            config = ProjectBackendConfig(
                project_id=project.id,
                provider="supabase",
                provider_project_id=result_data["project_ref"],
                provider_project_url=result_data["project_url"],
                status="active",
            )
            config.set_api_key_anon(result_data["anon_key"])
            config.set_api_key_service(result_data["service_role_key"])
            config.set_config_data(result_data)

        elif request.provider == "firebase":
            if not request.firebase_project_id:
                raise HTTPException(status_code=400, detail="firebase_project_id required")

            async with FirebaseOAuthService(access_token) as service:
                result_data = await service.provision_for_codi(
                    project_id=request.firebase_project_id,
                    app_name=project.name,
                )

            # Save config
            config = ProjectBackendConfig(
                project_id=project.id,
                provider="firebase",
                provider_project_id=result_data["project_id"],
                status="active",
            )
            config.set_api_key_anon(result_data["api_key"])
            config.set_config_data(result_data["config"])

        else:
            raise HTTPException(status_code=400, detail="Unsupported provider")

        session.add(config)

        # Update project backend_type
        project.backend_type = request.provider
        project.updated_at = datetime.now(timezone.utc)

        await session.commit()

        logger.info(f"Provisioned {request.provider} for project {project.id}")

        return {
            "success": True,
            "provider": request.provider,
            "project_url": config.provider_project_url,
            "message": f"Successfully configured {request.provider}",
        }

    except Exception as e:
        logger.error(f"Provisioning failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============ Manual Serverpod Config ============

@router.post("/serverpod/configure")
async def configure_serverpod(
    request: ServerpodConfigRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually configure Serverpod for a project."""
    # Verify project ownership
    result = await session.execute(
        select(Project).where(
            Project.id == request.project_id,
            Project.owner_id == current_user.id,
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create/update config
    result = await session.execute(
        select(ProjectBackendConfig).where(
            ProjectBackendConfig.project_id == request.project_id,
            ProjectBackendConfig.provider == "serverpod",
        )
    )
    config = result.scalar_one_or_none()

    if config:
        config.provider_project_url = request.server_url
        if request.api_key:
            config.set_api_key_anon(request.api_key)
        config.status = "active"
        config.updated_at = datetime.now(timezone.utc)
    else:
        config = ProjectBackendConfig(
            project_id=request.project_id,
            provider="serverpod",
            provider_project_url=request.server_url,
            status="active",
        )
        if request.api_key:
            config.set_api_key_anon(request.api_key)
        session.add(config)

    project.backend_type = "serverpod"
    project.updated_at = datetime.now(timezone.utc)

    await session.commit()

    return {
        "success": True,
        "provider": "serverpod",
        "message": "Serverpod configured successfully",
    }


# ============ Get Project Backend Config ============

@router.get("/project/{project_id}/config")
async def get_project_backend_config(
    project_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get backend configuration for a project (without secrets)."""
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

    # Get configs
    result = await session.execute(
        select(ProjectBackendConfig).where(
            ProjectBackendConfig.project_id == project_id,
        )
    )
    configs = result.scalars().all()

    return {
        "project_id": project_id,
        "backend_type": project.backend_type,
        "configs": [c.to_dict() for c in configs],
    }
