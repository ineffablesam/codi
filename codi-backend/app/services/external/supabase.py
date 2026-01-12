"""Supabase OAuth and Management API service.

Enables users to connect their Supabase accounts via OAuth and manage projects.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Supabase OAuth endpoints
SUPABASE_OAUTH_BASE = "https://api.supabase.com/v1/oauth"
SUPABASE_API_BASE = "https://api.supabase.com/v1"


class SupabaseOAuthService:
    """Service for Supabase OAuth and Management API operations."""

    def __init__(self, access_token: Optional[str] = None):
        """Initialize with optional access token for authenticated requests."""
        self.access_token = access_token
        self._client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> Dict[str, str]:
        """Generate OAuth authorization URL for user to authorize Codi.

        Users authorize Codi to access their Supabase account via OAuth.
        This uses Supabase's OAuth which requires the user to login and consent.

        Args:
            redirect_uri: Callback URL after authorization
            state: Optional state for CSRF protection

        Returns:
            Authorization URL and state
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            # Supabase uses scopes for Management API access
            "scope": "all",
        }

        auth_url = f"{SUPABASE_OAUTH_BASE}/authorize?{urlencode(params)}"

        return {
            "authorization_url": auth_url,
            "state": state,
        }

    async def exchange_code_for_tokens(
        self, code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            Token response with access_token, refresh_token, expires_in
        """
        response = await self._client.post(
            f"{SUPABASE_OAUTH_BASE}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise Exception(f"Token exchange failed: {response.status_code}")

        data = response.json()

        # Calculate expiry time
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at,
        }

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New token response
        """
        response = await self._client.post(
            f"{SUPABASE_OAUTH_BASE}/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise Exception("Token refresh failed")

        data = response.json()
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": expires_at,
        }

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def list_organizations(self) -> List[Dict[str, Any]]:
        """List user's Supabase organizations.

        Returns:
            List of organizations with id, name, billing info
        """
        response = await self._client.get(
            f"{SUPABASE_API_BASE}/organizations",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            logger.error(f"List organizations failed: {response.text}")
            raise Exception("Failed to list organizations")

        return response.json()

    async def list_projects(self) -> List[Dict[str, Any]]:
        """List all Supabase projects accessible to user.

        Returns:
            List of projects with ref, name, region, status
        """
        response = await self._client.get(
            f"{SUPABASE_API_BASE}/projects",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            logger.error(f"List projects failed: {response.text}")
            raise Exception("Failed to list projects")

        return response.json()

    async def create_project(
        self,
        organization_id: str,
        name: str,
        db_password: str,
        region: str = "us-east-1",
        plan: str = "free",
    ) -> Dict[str, Any]:
        """Create a new Supabase project.

        Args:
            organization_id: Organization to create project in
            name: Project name
            db_password: Database password
            region: AWS region for the project
            plan: Pricing plan (free, pro)

        Returns:
            Created project info with ref, url, keys
        """
        response = await self._client.post(
            f"{SUPABASE_API_BASE}/projects",
            headers=self._get_headers(),
            json={
                "organization_id": organization_id,
                "name": name,
                "db_pass": db_password,
                "region": region,
                "plan": plan,
            },
        )

        if response.status_code not in (200, 201):
            logger.error(f"Create project failed: {response.text}")
            raise Exception(f"Failed to create project: {response.text}")

        project = response.json()
        logger.info(f"Created Supabase project: {project.get('ref')}")

        return project

    async def get_project(self, project_ref: str) -> Dict[str, Any]:
        """Get project details.

        Args:
            project_ref: Project reference (unique ID)

        Returns:
            Project details
        """
        response = await self._client.get(
            f"{SUPABASE_API_BASE}/projects/{project_ref}",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            raise Exception("Failed to get project")

        return response.json()

    async def get_api_keys(self, project_ref: str) -> Dict[str, str]:
        """Get project API keys (anon and service_role).

        Args:
            project_ref: Project reference

        Returns:
            Dict with 'anon' and 'service_role' keys
        """
        response = await self._client.get(
            f"{SUPABASE_API_BASE}/projects/{project_ref}/api-keys",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            logger.error(f"Get API keys failed: {response.text}")
            raise Exception("Failed to get API keys")

        keys = response.json()
        result = {}

        for key in keys:
            if key.get("name") == "anon":
                result["anon"] = key["api_key"]
            elif key.get("name") == "service_role":
                result["service_role"] = key["api_key"]

        return result

    async def get_project_url(self, project_ref: str) -> str:
        """Get project URL.

        Args:
            project_ref: Project reference

        Returns:
            Project API URL (e.g., https://xxx.supabase.co)
        """
        return f"https://{project_ref}.supabase.co"

    async def provision_project_for_codi(
        self,
        organization_id: str,
        project_name: str,
    ) -> Dict[str, Any]:
        """Full provisioning flow: create project and get keys.

        Args:
            organization_id: Supabase organization ID
            project_name: Name for the new project

        Returns:
            Full project config with URL, anon_key, service_role_key
        """
        # Generate secure database password
        db_password = secrets.token_urlsafe(24)

        # Create project
        project = await self.create_project(
            organization_id=organization_id,
            name=project_name,
            db_password=db_password,
        )

        project_ref = project["ref"]

        # Wait for project to be ready (Supabase projects take ~1 min to provision)
        # In production, you'd poll the status or use webhooks
        import asyncio
        await asyncio.sleep(5)  # Initial wait

        # Get API keys
        keys = await self.get_api_keys(project_ref)

        return {
            "project_ref": project_ref,
            "project_url": await self.get_project_url(project_ref),
            "anon_key": keys.get("anon"),
            "service_role_key": keys.get("service_role"),
            "db_password": db_password,
        }

    async def execute_sql(self, project_ref: str, sql: str) -> Dict[str, Any]:
        """Execute SQL on a Supabase project (for schema setup).

        Args:
            project_ref: Project reference
            sql: SQL to execute

        Returns:
            Query result
        """
        response = await self._client.post(
            f"{SUPABASE_API_BASE}/projects/{project_ref}/database/query",
            headers=self._get_headers(),
            json={"query": sql},
        )

        if response.status_code != 200:
            logger.error(f"SQL execution failed: {response.text}")
            raise Exception(f"SQL execution failed: {response.text}")

        return response.json()
