"""Authentication dependencies for FastAPI."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.user import User
from app.utils.security import TokenPayload

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials
        session: Database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode and validate token
    payload = TokenPayload.from_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = payload.user_id
    if user_id is None:
        # Try to get from sub
        try:
            user_id = int(payload.sub)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    session: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """Get the current user if authenticated, None otherwise.

    Args:
        credentials: Optional HTTP Bearer credentials
        session: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None


def require_github_token(user: User = Depends(get_current_user)) -> str:
    """Require and return decrypted GitHub token.

    Args:
        user: Authenticated user

    Returns:
        Decrypted GitHub access token

    Raises:
        HTTPException: If user has no GitHub token
    """
    from app.services.encryption import encryption_service

    if not user.github_access_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub account not connected",
        )

    try:
        return encryption_service.decrypt_token(user.github_access_token_encrypted)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt GitHub token",
        )
