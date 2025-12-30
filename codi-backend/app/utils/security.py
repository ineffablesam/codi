"""Security utilities for JWT tokens and password hashing."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a hash from a password.

    Args:
        password: The plain text password to hash

    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def get_token_expiry_seconds() -> int:
    """Get token expiry time in seconds.

    Returns:
        Token expiry time in seconds
    """
    return settings.jwt_access_token_expire_minutes * 60


class TokenPayload:
    """Structured token payload for type safety."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        """Initialize token payload.

        Args:
            payload: Decoded JWT payload dictionary
        """
        self.sub: str = payload.get("sub", "")  # Subject (usually user ID)
        self.exp: datetime = datetime.fromtimestamp(
            payload.get("exp", 0), tz=timezone.utc
        )
        self.iat: datetime = datetime.fromtimestamp(
            payload.get("iat", 0), tz=timezone.utc
        )
        self.user_id: Optional[int] = payload.get("user_id")
        self.github_username: Optional[str] = payload.get("github_username")

    def is_expired(self) -> bool:
        """Check if token is expired.

        Returns:
            True if token is expired, False otherwise
        """
        return datetime.now(timezone.utc) > self.exp

    @classmethod
    def from_token(cls, token: str) -> Optional["TokenPayload"]:
        """Create TokenPayload from JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenPayload if valid, None otherwise
        """
        payload = decode_access_token(token)
        if payload is None:
            return None
        return cls(payload)
