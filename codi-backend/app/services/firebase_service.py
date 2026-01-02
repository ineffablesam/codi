"""Firebase OAuth and Management API service.

Enables users to connect their Google/Firebase accounts via OAuth and manage projects.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Google OAuth endpoints
GOOGLE_OAUTH_BASE = "https://accounts.google.com/o/oauth2/v2"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Firebase Management API
FIREBASE_API_BASE = "https://firebase.googleapis.com/v1beta1"


class FirebaseOAuthService:
    """Service for Firebase OAuth and Management API operations."""

    def __init__(self, access_token: Optional[str] = None):
        """Initialize with optional access token for authenticated requests."""
        self.access_token = access_token
        self._client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    def get_authorization_url(
        self, redirect_uri: str, state: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate Google OAuth authorization URL.

        Users authorize Codi to access their Firebase/GCP account.

        Args:
            redirect_uri: Callback URL after authorization
            state: Optional state for CSRF protection

        Returns:
            Authorization URL and state
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        # Required scopes for Firebase Management
        scopes = [
            "https://www.googleapis.com/auth/firebase",
            "https://www.googleapis.com/auth/cloud-platform",
        ]

        params = {
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }

        # Note: client_id comes from user's own Google Cloud Console
        # Each user provides their own credentials via OAuth
        auth_url = f"{GOOGLE_OAUTH_BASE}/auth?{urlencode(params)}"

        return {
            "authorization_url": auth_url,
            "state": state,
        }

    async def exchange_code_for_tokens(
        self, code: str, redirect_uri: str, client_id: str, client_secret: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in authorization
            client_id: User's Google OAuth client ID
            client_secret: User's Google OAuth client secret

        Returns:
            Token response with access_token, refresh_token, expires_in
        """
        response = await self._client.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise Exception(f"Token exchange failed: {response.status_code}")

        data = response.json()
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": expires_at,
        }

    async def refresh_tokens(
        self, refresh_token: str, client_id: str, client_secret: str
    ) -> Dict[str, Any]:
        """Refresh expired access token.

        Args:
            refresh_token: The refresh token
            client_id: User's Google OAuth client ID
            client_secret: User's Google OAuth client secret

        Returns:
            New token response
        """
        response = await self._client.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
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

    async def list_projects(self) -> List[Dict[str, Any]]:
        """List Firebase projects accessible to user.

        Returns:
            List of Firebase projects
        """
        response = await self._client.get(
            f"{FIREBASE_API_BASE}/projects",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            logger.error(f"List projects failed: {response.text}")
            raise Exception("Failed to list Firebase projects")

        data = response.json()
        return data.get("results", [])

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get Firebase project details.

        Args:
            project_id: Firebase project ID

        Returns:
            Project details
        """
        response = await self._client.get(
            f"{FIREBASE_API_BASE}/projects/{project_id}",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            raise Exception("Failed to get Firebase project")

        return response.json()

    async def add_firebase_to_gcp_project(self, gcp_project_id: str) -> Dict[str, Any]:
        """Add Firebase to an existing GCP project.

        Args:
            gcp_project_id: Google Cloud project ID

        Returns:
            Firebase project info
        """
        response = await self._client.post(
            f"{FIREBASE_API_BASE}/projects/{gcp_project_id}:addFirebase",
            headers=self._get_headers(),
            json={},
        )

        if response.status_code not in (200, 201):
            logger.error(f"Add Firebase failed: {response.text}")
            raise Exception(f"Failed to add Firebase: {response.text}")

        return response.json()

    async def create_web_app(
        self, project_id: str, display_name: str
    ) -> Dict[str, Any]:
        """Create a Firebase web app.

        Args:
            project_id: Firebase project ID
            display_name: Display name for the web app

        Returns:
            Web app info including app ID
        """
        response = await self._client.post(
            f"{FIREBASE_API_BASE}/projects/{project_id}/webApps",
            headers=self._get_headers(),
            json={"displayName": display_name},
        )

        if response.status_code not in (200, 201):
            logger.error(f"Create web app failed: {response.text}")
            raise Exception("Failed to create web app")

        return response.json()

    async def get_web_app_config(self, project_id: str, app_id: str) -> Dict[str, Any]:
        """Get Firebase web app configuration.

        Args:
            project_id: Firebase project ID
            app_id: Web app ID

        Returns:
            Firebase config object for web SDK
        """
        response = await self._client.get(
            f"{FIREBASE_API_BASE}/projects/{project_id}/webApps/{app_id}/config",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            raise Exception("Failed to get web app config")

        return response.json()

    async def list_web_apps(self, project_id: str) -> List[Dict[str, Any]]:
        """List web apps in a Firebase project.

        Args:
            project_id: Firebase project ID

        Returns:
            List of web apps
        """
        response = await self._client.get(
            f"{FIREBASE_API_BASE}/projects/{project_id}/webApps",
            headers=self._get_headers(),
        )

        if response.status_code != 200:
            raise Exception("Failed to list web apps")

        data = response.json()
        return data.get("apps", [])

    async def provision_for_codi(
        self, project_id: str, app_name: str
    ) -> Dict[str, Any]:
        """Full provisioning flow: create web app and get config.

        Args:
            project_id: Firebase project ID
            app_name: Name for the web app

        Returns:
            Full Firebase config for web SDK
        """
        # Create web app
        web_app = await self.create_web_app(project_id, app_name)
        
        # Extract app ID from the name (format: projects/{id}/webApps/{appId})
        app_name_parts = web_app.get("name", "").split("/")
        app_id = app_name_parts[-1] if app_name_parts else None

        if not app_id:
            raise Exception("Failed to get web app ID")

        # Get config
        import asyncio
        await asyncio.sleep(2)  # Brief wait for provisioning
        
        config = await self.get_web_app_config(project_id, app_id)

        return {
            "project_id": project_id,
            "app_id": app_id,
            "api_key": config.get("apiKey"),
            "auth_domain": config.get("authDomain"),
            "storage_bucket": config.get("storageBucket"),
            "messaging_sender_id": config.get("messagingSenderId"),
            "measurement_id": config.get("measurementId"),
            "config": config,
        }
