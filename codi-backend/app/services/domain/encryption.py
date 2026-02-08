"""Encryption service for secure token storage."""
import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using Fernet."""

    _instance: Optional["EncryptionService"] = None
    _fernet: Optional[Fernet] = None

    def __new__(cls) -> "EncryptionService":
        """Singleton pattern to ensure single Fernet instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the encryption service with the configured key."""
        if self._fernet is None:
            self._initialize_fernet()

    def _initialize_fernet(self) -> None:
        """Initialize the Fernet cipher with the encryption key."""
        key = settings.encryption_key

        if not key:
            # Generate a new key if not configured (for development)
            key = Fernet.generate_key().decode()
            logger.warning(
                "No encryption key configured, generated temporary key. "
                "Set ENCRYPTION_KEY in production!"
            )

        try:
            # Ensure key is properly formatted
            if isinstance(key, str):
                # Check if it's a valid base64 Fernet key
                try:
                    key_bytes = key.encode() if isinstance(key, str) else key
                    self._fernet = Fernet(key_bytes)
                except ValueError:
                    # If not valid, try to create a key from the string
                    # by padding/hashing it to 32 bytes
                    key_bytes = self._derive_key(key)
                    self._fernet = Fernet(base64.urlsafe_b64encode(key_bytes))
            else:
                self._fernet = Fernet(key)

            logger.debug("Encryption service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            # Generate a fallback key for development
            self._fernet = Fernet(Fernet.generate_key())

    def _derive_key(self, password: str) -> bytes:
        """Derive a 32-byte key from a password string.

        Uses a simple approach for development; in production,
        use a proper key derivation function like PBKDF2.

        Args:
            password: Password string to derive key from

        Returns:
            32-byte key suitable for Fernet
        """
        import hashlib
        # Use SHA-256 to get exactly 32 bytes
        return hashlib.sha256(password.encode()).digest()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not self._fernet:
            raise RuntimeError("Encryption service not initialized")

        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted string.

        Args:
            ciphertext: The encrypted string to decrypt

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails (invalid token or key)
        """
        if not self._fernet:
            raise RuntimeError("Encryption service not initialized")

        try:
            decrypted_bytes = self._fernet.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except InvalidToken as e:
            logger.error(f"Decryption failed - invalid token: {e}")
            raise ValueError("Failed to decrypt data - invalid token or key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def encrypt_token(self, token: str) -> str:
        """Encrypt an access token for storage.

        This is a convenience method specifically for GitHub tokens.

        Args:
            token: The access token to encrypt

        Returns:
            Encrypted token string
        """
        return self.encrypt(token)

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a stored access token.

        Args:
            encrypted_token: The encrypted token to decrypt

        Returns:
            Decrypted access token
        """
        return self.decrypt(encrypted_token)

    @classmethod
    def generate_key(cls) -> str:
        """Generate a new Fernet-compatible encryption key.

        Useful for initial setup.

        Returns:
            Base64-encoded Fernet key
        """
        return Fernet.generate_key().decode()


# Global encryption service instance
encryption_service = EncryptionService()
