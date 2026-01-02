
import httpx
from typing import Dict, Any, Optional

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VercelService:
    """Service for Vercel OAuth and API operations."""

    VERCEL_OAUTH_URL = "https://vercel.com/oauth/authorize"
    VERCEL_TOKEN_URL = "https://api.vercel.com/v2/oauth/access_token"
    VERCEL_API_URL = "https://api.vercel.com"

    @classmethod
    def get_oauth_url(cls, redirect_uri: str, state: Optional[str] = None) -> str:
        """Generate Vercel OAuth authorization URL.

        Args:
            redirect_uri: The callback URL
            state: Optional state parameter for CSRF protection

        Returns:
            Vercel OAuth authorization URL
        """
        from urllib.parse import urlencode

        slug = settings.vercel_integration_slug
        base_url = f"https://vercel.com/integrations/{slug}/new"
        
        # For Integrations, we just pass state (client_id/redirect_uri are configured in dashboard)
        params = {}
        if state:
            params["state"] = state

        if not params:
            return base_url
            
        return f"{base_url}?{urlencode(params)}"

    @classmethod
    async def exchange_code_for_token(cls, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth authorization code for access token.

        Args:
            code: Authorization code from Vercel OAuth callback
            redirect_uri: The callback URL used in the authorization request

        Returns:
            Dictionary containing access_token, user_id, team_id, etc.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    cls.VERCEL_TOKEN_URL,
                    data={
                        "client_id": settings.vercel_client_id,
                        "client_secret": settings.vercel_client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Vercel token exchange failed: {response.text}")
                    raise ValueError(f"Failed to exchange code for token: {response.text}")

                data = response.json()
                
                # Check for errors in 200 response (some APIs do this, Vercel usually doesn't but safe to check)
                if "error" in data:
                     raise ValueError(f"Vercel OAuth Error: {data.get('error_description', data['error'])}")

                return {
                    "access_token": data["access_token"],
                    "token_type": data.get("token_type", "Bearer"),
                    "team_id": data.get("team_id"), # If installed for a team
                    "user_id": data.get("user_id"), # Installing user
                }

            except httpx.RequestError as e:
                logger.error(f"Vercel OAuth request error: {e}")
                raise ValueError("Network error during Vercel authentication")

    @classmethod
    async def get_user_info(cls, access_token: str) -> Dict[str, Any]:
        """Get Vercel user information.
        
        Args:
            access_token: Vercel access token
            
        Returns:
            Dictionary with user info
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{cls.VERCEL_API_URL}/v2/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get Vercel user info: {response.text}")
                # We can still return a partial object if just the token works, 
                # but better to raise to signal invalid token
                raise ValueError("Failed to get Vercel user information")
                
            data = response.json()
            user = data.get("user", {})
            return {
                "id": user.get("id"),
                "username": user.get("username"),
                "email": user.get("email"),
                "name": user.get("name"),
                "avatar": f"https://vercel.com/api/www/avatar/{user.get('avatar')}" if user.get("avatar") else None
            }
