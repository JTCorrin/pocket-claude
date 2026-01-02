"""
Token encryption and decryption using Fernet (symmetric encryption).
"""
import logging
from cryptography.fernet import Fernet
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like OAuth tokens."""

    def __init__(self):
        """Initialize encryption service with key from settings."""
        settings = get_settings()
        if not settings.ENCRYPTION_KEY:
            raise ValueError(
                "ENCRYPTION_KEY environment variable must be set. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            self._fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        except Exception as e:
            raise ValueError(
                f"Invalid ENCRYPTION_KEY format: {e}. "
                "Generate a valid key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            ) from e

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string, or empty string if plaintext is empty

        Note:
            Empty strings are returned as-is without encryption. This is intentional
            to allow for optional fields that may be null/empty. Callers should validate
            that critical fields are non-empty before calling this method.
        """
        if not plaintext:
            return ""

        encrypted = self._fernet.encrypt(plaintext.encode())
        return encrypted.decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a ciphertext string.

        Args:
            ciphertext: The base64-encoded encrypted string

        Returns:
            Decrypted plaintext string, or empty string if ciphertext is empty

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails

        Note:
            Empty strings are returned as-is without decryption. This matches the
            behavior of the encrypt method for optional fields.
        """
        if not ciphertext:
            return ""

        decrypted = self._fernet.decrypt(ciphertext.encode())
        return decrypted.decode()


# Global encryption service instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get or create the global encryption service."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
        logger.info("Created encryption service")
    return _encryption_service
