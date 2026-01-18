"""Authentication API endpoints."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.models.user import User
from app.schemas.user import TokenResponse, UserResponse
from app.services.domain.encryption import encryption_service
from app.services.external.github import GitHubService
from app.utils.logging import get_logger
from app.utils.security import create_access_token

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Store OAuth states temporarily (in production, use Redis)
_oauth_states: Dict[str, datetime] = {}


@router.get("/github")
async def github_oauth_redirect() -> Dict[str, str]:
    """Get GitHub OAuth authorization URL.

    Returns:
        Dictionary with authorization URL and state
    """
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = datetime.now(timezone.utc)

    # Clean up old states (older than 10 minutes)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired = [s for s, t in _oauth_states.items() if t < cutoff]
    for s in expired:
        _oauth_states.pop(s, None)

    url = GitHubService.get_oauth_url(state=state)

    return {
        "url": url,
        "state": state,
    }


@router.get("/github/callback")
async def github_oauth_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Handle GitHub OAuth callback and create/update user.

    Args:
        code: Authorization code from GitHub
        state: State parameter for CSRF validation
        session: Database session

    Returns:
        JWT access token and user info
    """
    # Validate state
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter",
        )
    _oauth_states.pop(state)

    try:
        # Exchange code for access token
        token_data = await GitHubService.exchange_code_for_token(code)
        access_token = token_data["access_token"]

        # Get user info from GitHub
        github_user = await GitHubService.get_user_info(access_token)

        github_id = github_user["id"]
        github_username = github_user["login"]

        # Check if user exists
        result = await session.execute(
            select(User).where(User.github_id == github_id)
        )
        user = result.scalar_one_or_none()

        # Encrypt the GitHub token
        encrypted_token = encryption_service.encrypt_token(access_token)
        is_new_user = False

        if user:
            # Update existing user
            user.github_username = github_username
            user.github_access_token_encrypted = encrypted_token
            user.github_avatar_url = github_user.get("avatar_url")
            user.email = github_user.get("email") or user.email
            user.name = github_user.get("name") or user.name
            user.last_login_at = datetime.now(timezone.utc)

            logger.info(f"User logged in: {github_username}")
        else:
            # Create new user
            is_new_user = True
            user = User(
                github_id=github_id,
                github_username=github_username,
                github_access_token_encrypted=encrypted_token,
                github_avatar_url=github_user.get("avatar_url"),
                email=github_user.get("email"),
                name=github_user.get("name"),
                last_login_at=datetime.now(timezone.utc),
            )
            session.add(user)

            logger.info(f"New user created: {github_username}")

        await session.commit()
        await session.refresh(user)

        # Create JWT token
        jwt_token = create_access_token(
            data={
                "sub": str(user.id),
                "user_id": user.id,
                "github_username": user.github_username,
            }
        )

        return TokenResponse(
            access_token=jwt_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user=UserResponse(
                id=user.id,
                github_id=user.github_id,
                github_username=user.github_username,
                email=user.email,
                name=user.name,
                github_avatar_url=user.github_avatar_url,
                is_active=user.is_active,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            ),
            is_new_user=is_new_user,
        )

    except ValueError as e:
        logger.error(f"GitHub OAuth failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    session: AsyncSession = Depends(get_db_session),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> UserResponse:
    """Get current authenticated user.

    Returns:
        Current user information
    """
    from app.api.v1.deps import get_current_user

    user = await get_current_user(credentials, session)

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        email=user.email,
        name=user.name,
        github_avatar_url=user.github_avatar_url,
        what_brings_you=user.what_brings_you,
        coding_experience=user.coding_experience,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.patch("/me/onboarding", response_model=UserResponse)
async def complete_onboarding(
    onboarding_data: "OnboardingUpdate",
    session: AsyncSession = Depends(get_db_session),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> UserResponse:
    """Complete user onboarding by saving required profile fields.

    Args:
        onboarding_data: Required onboarding fields (name, what_brings_you, coding_experience)

    Returns:
        Updated user information
    """
    from app.api.v1.deps import get_current_user
    from app.schemas.user import OnboardingUpdate

    user = await get_current_user(credentials, session)

    # Update user with onboarding data
    user.name = onboarding_data.name
    user.what_brings_you = onboarding_data.what_brings_you
    user.coding_experience = onboarding_data.coding_experience

    await session.commit()
    await session.refresh(user)

    logger.info(f"User {user.github_username} completed onboarding")

    return UserResponse(
        id=user.id,
        github_id=user.github_id,
        github_username=user.github_username,
        email=user.email,
        name=user.name,
        github_avatar_url=user.github_avatar_url,
        what_brings_you=user.what_brings_you,
        coding_experience=user.coding_experience,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post("/logout")
async def logout() -> Dict[str, str]:
    """Logout the current user (client should discard token).

    Returns:
        Success message
    """
    # JWT tokens are stateless, so we just return success
    # Client should discard the token
    return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Refresh the access token.

    Note: This requires the current token to still be valid.

    Returns:
        New JWT access token
    """
    from app.api.v1.deps import get_current_user

    # This would need proper implementation with refresh tokens
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Refresh token not implemented - use GitHub OAuth flow",
    )
