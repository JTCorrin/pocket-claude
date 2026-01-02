"""
Git provider OAuth and connection management with database storage.
"""
import asyncio
import secrets
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.git_models import (
    GitProvider,
    GitConnection,
    GitConnectionStatus,
    OAuthInitiateResponse,
)
from app.models.db_models import GitConnectionDB
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.config import get_settings
from app.core.database import get_session
from app.core.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Constants
MAX_ERROR_MESSAGE_LENGTH = 200  # Maximum length for error message snippets
OAUTH_STATE_EXPIRY_MINUTES = 15  # OAuth states expire after 15 minutes
TOKEN_REFRESH_BUFFER_MINUTES = 10  # Refresh token this many minutes before expiry


class GitProviderConfig:
    """Configuration for git providers."""

    GITHUB = {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "api_url": "https://api.github.com",
        "user_endpoint": "/user",
        "scopes": ["repo", "user:email"],
    }

    GITLAB = {
        "auth_url_template": "{instance}/oauth/authorize",
        "token_url_template": "{instance}/oauth/token",
        "api_url_template": "{instance}/api/v4",
        "user_endpoint": "/user",
        "scopes": ["api", "read_user", "read_repository", "write_repository"],
    }

    GITEA = {
        "auth_url_template": "{instance}/login/oauth/authorize",
        "token_url_template": "{instance}/login/oauth/access_token",
        "api_url_template": "{instance}/api/v1",
        "user_endpoint": "/user",
        "scopes": ["read:user", "read:repository", "write:repository"],
    }


class GitService:
    """
    Service for managing git provider connections and OAuth flow.

    Uses Authorization Code Flow with PKCE (Proof Key for Code Exchange)
    for secure OAuth without client secrets (suitable for public clients).

    Tokens are stored encrypted in the database and automatically refreshed
    before expiration.
    """

    def __init__(self):
        """Initialize git service."""
        # OAuth states still in-memory (temporary, 15 min expiry)
        self._oauth_states: Dict[str, Dict[str, Any]] = {}
        self._settings = get_settings()
        self._encryption = get_encryption_service()
        # Lock to prevent concurrent token refresh for the same connection
        self._refresh_locks: Dict[str, asyncio.Lock] = {}

        logger.info("GitService initialized with database storage and encryption")

    def _validate_pkce_parameter(self, value: str, param_name: str) -> None:
        """
        Validate PKCE parameter according to RFC 7636.

        Args:
            value: The PKCE parameter value
            param_name: Name of the parameter (for error messages)

        Raises:
            BadRequestException: If parameter doesn't meet RFC 7636 requirements
        """
        # RFC 7636: code_verifier and code_challenge must be base64url-encoded
        # and contain only [A-Z, a-z, 0-9, -, _, ~] characters
        if not re.match(r'^[A-Za-z0-9\-_~]+$', value):
            raise BadRequestException(
                f"{param_name} must contain only base64url characters [A-Z, a-z, 0-9, -, _, ~]"
            )

    def _validate_instance_url(self, url: str) -> None:
        """
        Validate instance URL for security.

        Args:
            url: The instance URL to validate

        Raises:
            BadRequestException: If URL is invalid or insecure
        """
        if not url.startswith('https://'):
            raise BadRequestException(
                "Instance URL must use HTTPS for security. HTTP URLs are not allowed."
            )

        # Basic URL structure validation
        # Pattern: https://hostname(:port)(/path)
        # Hostname can be domain or IP, but must be well-formed
        if not re.match(r'^https://[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*(:[0-9]+)?(/.*)?$', url):
            raise BadRequestException(
                "Invalid instance URL format. Must be a valid HTTPS URL."
            )

    def _cleanup_expired_oauth_states(self) -> None:
        """
        Clean up expired OAuth states (older than OAUTH_STATE_EXPIRY_MINUTES).

        This prevents the OAuth state dictionary from growing indefinitely
        with abandoned or failed OAuth attempts.
        """
        now = datetime.now(timezone.utc)
        expiry_time = timedelta(minutes=OAUTH_STATE_EXPIRY_MINUTES)

        expired_states = [
            state_id
            for state_id, state_data in self._oauth_states.items()
            if now - state_data["created_at"] > expiry_time
        ]

        for state_id in expired_states:
            del self._oauth_states[state_id]
            logger.debug(f"Cleaned up expired OAuth state: {state_id}")

        if expired_states:
            logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")

    def _db_connection_to_api(self, db_connection: GitConnectionDB) -> GitConnection:
        """
        Convert database GitConnectionDB model to API GitConnection model.

        Args:
            db_connection: Database model

        Returns:
            API model (without sensitive token data)
        """
        return GitConnection(
            id=db_connection.id,
            provider=GitProvider(db_connection.provider),
            instance_url=db_connection.instance_url,
            username=db_connection.username,
            email=db_connection.email,
            connected_at=db_connection.connected_at,
            is_active=db_connection.is_active,
        )

    def initiate_oauth(
        self,
        provider: GitProvider,
        code_challenge: str,
        code_challenge_method: str,
        redirect_uri: str,
        instance_url: Optional[str] = None,
    ) -> OAuthInitiateResponse:
        """
        Initiate OAuth flow with PKCE.

        Args:
            provider: Git provider (GitHub, GitLab, Gitea)
            code_challenge: PKCE code challenge (SHA256(code_verifier))
            code_challenge_method: Challenge method (S256 or plain)
            redirect_uri: OAuth redirect URI
            instance_url: Custom instance URL for self-hosted providers

        Returns:
            Authorization URL and state

        Raises:
            BadRequestException: If instance URL required but not provided
        """
        # Validate PKCE parameters
        self._validate_pkce_parameter(code_challenge, "code_challenge")

        # Validate instance URL for self-hosted providers
        if provider in (GitProvider.GITLAB, GitProvider.GITEA):
            if not instance_url:
                raise BadRequestException(
                    f"{provider.value} requires instance_url for self-hosted instances"
                )
            self._validate_instance_url(instance_url)

        # Clean up expired OAuth states
        self._cleanup_expired_oauth_states()

        # Generate secure random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Get provider configuration and client_id
        if provider == GitProvider.GITHUB:
            config = GitProviderConfig.GITHUB
            auth_url = config["auth_url"]
            scopes = config["scopes"]
            client_id = self._settings.GITHUB_CLIENT_ID
        elif provider == GitProvider.GITLAB:
            config = GitProviderConfig.GITLAB
            auth_url = config["auth_url_template"].format(instance=instance_url)
            scopes = config["scopes"]
            client_id = self._settings.GITLAB_CLIENT_ID
        else:  # GITEA
            config = GitProviderConfig.GITEA
            auth_url = config["auth_url_template"].format(instance=instance_url)
            scopes = config["scopes"]
            client_id = self._settings.GITEA_CLIENT_ID

        # Build authorization URL with PKCE parameters
        params = {
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        }

        # Add client_id if configured
        if client_id:
            params["client_id"] = client_id
        else:
            logger.warning(
                f"No client_id configured for {provider.value}. "
                f"OAuth flow will likely fail. Set {provider.value.upper()}_CLIENT_ID "
                "environment variable."
            )

        authorization_url = f"{auth_url}?{urlencode(params)}"

        # Store state for verification (still in-memory, temporary)
        self._oauth_states[state] = {
            "provider": provider.value,
            "instance_url": instance_url,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(timezone.utc),
        }

        logger.info(f"Initiated OAuth for {provider.value} with state {state}")

        return OAuthInitiateResponse(
            authorization_url=authorization_url, state=state
        )

    async def handle_oauth_callback(
        self,
        provider: GitProvider,
        code: str,
        state: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> GitConnection:
        """
        Handle OAuth callback and exchange code for token.

        Tokens are encrypted and stored in the database.

        Args:
            provider: Git provider
            code: Authorization code from provider
            state: OAuth state for verification
            code_verifier: PKCE code verifier
            redirect_uri: OAuth redirect URI

        Returns:
            Created git connection

        Raises:
            BadRequestException: If state invalid or token exchange fails
            NotFoundException: If state not found
        """
        # Validate PKCE code_verifier
        self._validate_pkce_parameter(code_verifier, "code_verifier")

        # Verify state
        if state not in self._oauth_states:
            raise NotFoundException(f"OAuth state not found: {state}")

        stored_oauth_state = self._oauth_states[state]

        # Verify provider matches
        if stored_oauth_state["provider"] != provider.value:
            raise BadRequestException("Provider mismatch")

        # Verify redirect URI
        if stored_oauth_state["redirect_uri"] != redirect_uri:
            raise BadRequestException("Redirect URI mismatch")

        instance_url = stored_oauth_state.get("instance_url")

        # Get provider configuration and client_id
        if provider == GitProvider.GITHUB:
            config = GitProviderConfig.GITHUB
            token_url = config["token_url"]
            api_url = config["api_url"]
            user_endpoint = config["user_endpoint"]
            client_id = self._settings.GITHUB_CLIENT_ID
        elif provider == GitProvider.GITLAB:
            config = GitProviderConfig.GITLAB
            token_url = config["token_url_template"].format(instance=instance_url)
            api_url = config["api_url_template"].format(instance=instance_url)
            user_endpoint = config["user_endpoint"]
            client_id = self._settings.GITLAB_CLIENT_ID
        else:  # GITEA
            config = GitProviderConfig.GITEA
            token_url = config["token_url_template"].format(instance=instance_url)
            api_url = config["api_url_template"].format(instance=instance_url)
            user_endpoint = config["user_endpoint"]
            client_id = self._settings.GITEA_CLIENT_ID

        # Exchange code for token using PKCE
        async with httpx.AsyncClient() as client:
            token_data_payload = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            }

            # Add client_id if configured
            if client_id:
                token_data_payload["client_id"] = client_id

            token_response = await client.post(
                token_url,
                data=token_data_payload,
                headers={"Accept": "application/json"},
            )

            if token_response.status_code != 200:
                error_message = f"Token exchange failed: {token_response.status_code}"
                error_details = None

                # Parse error response for details
                try:
                    error_body = token_response.json()
                    if isinstance(error_body, dict):
                        error_code = error_body.get("error") or error_body.get("error_code")
                        error_desc = error_body.get("error_description") or error_body.get("error_message")
                        parts = []
                        if error_code:
                            parts.append(f"code={error_code}")
                        if error_desc:
                            parts.append(f"description={error_desc}")
                        if parts:
                            error_details = ", ".join(parts)
                        elif error_body:
                            error_details = str(error_body)
                except (ValueError, Exception):
                    # Response is not JSON or parsing failed
                    if token_response.text:
                        error_details = token_response.text[:MAX_ERROR_MESSAGE_LENGTH]  # Limit length

                if error_details:
                    error_message = f"{error_message} - {error_details}"

                logger.error(error_message)
                raise BadRequestException(error_message)

            token_data = token_response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")  # Seconds until expiration

            if not access_token:
                raise BadRequestException("No access token in response")

            # Calculate token expiration time
            token_expires_at = None
            if expires_in:
                token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Get user info
            user_response = await client.get(
                f"{api_url}{user_endpoint}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code != 200:
                raise BadRequestException("Failed to fetch user info")

            user_data = user_response.json()

        # Create database connection with encrypted tokens
        connection_id = secrets.token_urlsafe(16)

        # Encrypt tokens before storage
        access_token_encrypted = self._encryption.encrypt(access_token)
        refresh_token_encrypted = (
            self._encryption.encrypt(refresh_token) if refresh_token else None
        )

        # Store in database
        async with get_session() as session:
            db_connection = GitConnectionDB(
                id=connection_id,
                provider=provider.value,
                instance_url=instance_url,
                username=user_data.get("login") or user_data.get("username"),
                email=user_data.get("email"),
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=token_expires_at,
                scopes=config["scopes"],
                connected_at=datetime.now(timezone.utc),
                is_active=True,
            )

            session.add(db_connection)
            await session.commit()

        # Clean up OAuth state
        del self._oauth_states[state]

        logger.info(
            f"Created git connection {connection_id} for {provider.value} user {db_connection.username} "
            f"(tokens encrypted and stored in database)"
        )

        return self._db_connection_to_api(db_connection)

    async def get_connection(self, connection_id: str) -> GitConnection:
        """
        Get git connection by ID.

        Args:
            connection_id: Connection identifier

        Returns:
            Git connection

        Raises:
            NotFoundException: If connection not found
        """
        async with get_session() as session:
            result = await session.execute(
                select(GitConnectionDB).where(GitConnectionDB.id == connection_id)
            )
            db_connection = result.scalar_one_or_none()

            if not db_connection:
                raise NotFoundException(f"Connection not found: {connection_id}")

            return self._db_connection_to_api(db_connection)

    async def list_connections(self) -> list[GitConnection]:
        """
        List all active git connections.

        Returns:
            List of git connections
        """
        async with get_session() as session:
            result = await session.execute(
                select(GitConnectionDB).where(GitConnectionDB.is_active == True)
            )
            db_connections = result.scalars().all()

            return [self._db_connection_to_api(conn) for conn in db_connections]

    async def delete_connection(self, connection_id: str) -> None:
        """
        Delete a git connection.

        Args:
            connection_id: Connection identifier

        Raises:
            NotFoundException: If connection not found
        """
        async with get_session() as session:
            result = await session.execute(
                select(GitConnectionDB).where(GitConnectionDB.id == connection_id)
            )
            db_connection = result.scalar_one_or_none()

            if not db_connection:
                raise NotFoundException(f"Connection not found: {connection_id}")

            await session.delete(db_connection)
            await session.commit()

        logger.info(f"Deleted git connection {connection_id}")

    async def get_decrypted_token(self, connection_id: str) -> str:
        """
        Get decrypted access token for a connection.

        Automatically refreshes the token if it's expired or about to expire.

        Args:
            connection_id: Connection identifier

        Returns:
            Decrypted access token

        Raises:
            NotFoundException: If connection not found
        """
        async with get_session() as session:
            result = await session.execute(
                select(GitConnectionDB).where(GitConnectionDB.id == connection_id)
            )
            db_connection = result.scalar_one_or_none()

            if not db_connection:
                raise NotFoundException(f"Connection not found: {connection_id}")

            # Check if token needs refresh
            now = datetime.now(timezone.utc)
            needs_refresh = False

            if db_connection.token_expires_at:
                refresh_threshold = db_connection.token_expires_at - timedelta(
                    minutes=TOKEN_REFRESH_BUFFER_MINUTES
                )
                needs_refresh = now >= refresh_threshold

            if needs_refresh and db_connection.refresh_token_encrypted:
                # Get or create a lock for this connection to prevent concurrent refresh
                if connection_id not in self._refresh_locks:
                    self._refresh_locks[connection_id] = asyncio.Lock()
                
                async with self._refresh_locks[connection_id]:
                    # Re-check if token still needs refresh after acquiring lock
                    # (another request might have already refreshed it)
                    await session.refresh(db_connection)
                    if db_connection.token_expires_at:
                        refresh_threshold = db_connection.token_expires_at - timedelta(
                            minutes=TOKEN_REFRESH_BUFFER_MINUTES
                        )
                        needs_refresh = now >= refresh_threshold
                    
                    if needs_refresh:
                        logger.info(f"Token for connection {connection_id} needs refresh, attempting refresh")
                        try:
                            await self._refresh_token(session, db_connection)
                        except Exception as e:
                            logger.error(
                                f"Token refresh failed for connection {connection_id}: {e}",
                                exc_info=True,
                            )
                            # Fail fast instead of continuing with a potentially expired token
                            raise BadRequestException(
                                "Failed to refresh access token for Git connection; "
                                "please re-authenticate and try again."
                            ) from e

            # Decrypt and return access token
            return self._encryption.decrypt(db_connection.access_token_encrypted)

    async def _refresh_token(
        self, session: AsyncSession, db_connection: GitConnectionDB
    ) -> None:
        """
        Refresh an expired or soon-to-expire access token.

        Updates the db_connection object with new tokens but does NOT commit.
        The caller is responsible for committing the session.

        Args:
            session: Database session (caller must commit)
            db_connection: Database connection object to update

        Raises:
            BadRequestException: If token refresh fails
        """
        if not db_connection.refresh_token_encrypted:
            raise BadRequestException("No refresh token available for this connection")

        # Decrypt refresh token
        refresh_token = self._encryption.decrypt(db_connection.refresh_token_encrypted)

        # Get provider configuration
        provider = GitProvider(db_connection.provider)
        if provider == GitProvider.GITHUB:
            config = GitProviderConfig.GITHUB
            token_url = config["token_url"]
            client_id = self._settings.GITHUB_CLIENT_ID
        elif provider == GitProvider.GITLAB:
            config = GitProviderConfig.GITLAB
            token_url = config["token_url_template"].format(instance=db_connection.instance_url)
            client_id = self._settings.GITLAB_CLIENT_ID
        else:  # GITEA
            config = GitProviderConfig.GITEA
            token_url = config["token_url_template"].format(instance=db_connection.instance_url)
            client_id = self._settings.GITEA_CLIENT_ID

        # Request new token using refresh token
        async with httpx.AsyncClient() as client:
            token_data_payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }

            if client_id:
                token_data_payload["client_id"] = client_id

            token_response = await client.post(
                token_url,
                data=token_data_payload,
                headers={"Accept": "application/json"},
            )

            if token_response.status_code != 200:
                error_msg = f"Token refresh failed: {token_response.status_code}"
                logger.error(error_msg)
                raise BadRequestException(error_msg)

            token_data = token_response.json()
            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in")

            if not new_access_token:
                raise BadRequestException("No access token in refresh response")

            # Update database with new tokens
            db_connection.access_token_encrypted = self._encryption.encrypt(new_access_token)

            if new_refresh_token:
                db_connection.refresh_token_encrypted = self._encryption.encrypt(new_refresh_token)

            if expires_in:
                db_connection.token_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=expires_in
                )

            db_connection.last_used_at = datetime.now(timezone.utc)

            # Note: Session commit is handled by the caller's context manager

            logger.info(f"Successfully refreshed token for connection {db_connection.id}")

    async def check_connection_status(
        self, connection_id: str
    ) -> GitConnectionStatus:
        """
        Check if a git connection is still valid.

        Args:
            connection_id: Connection identifier

        Returns:
            Connection status

        Raises:
            NotFoundException: If connection not found
        """
        async with get_session() as session:
            result = await session.execute(
                select(GitConnectionDB).where(GitConnectionDB.id == connection_id)
            )
            db_connection = result.scalar_one_or_none()

            if not db_connection:
                raise NotFoundException(f"Connection not found: {connection_id}")

            # Get provider configuration
            provider = GitProvider(db_connection.provider)
            if provider == GitProvider.GITHUB:
                config = GitProviderConfig.GITHUB
                api_url = config["api_url"]
                user_endpoint = config["user_endpoint"]
            elif provider == GitProvider.GITLAB:
                config = GitProviderConfig.GITLAB
                api_url = config["api_url_template"].format(instance=db_connection.instance_url)
                user_endpoint = config["user_endpoint"]
            else:  # GITEA
                config = GitProviderConfig.GITEA
                api_url = config["api_url_template"].format(instance=db_connection.instance_url)
                user_endpoint = config["user_endpoint"]

            # Get decrypted token (will auto-refresh if needed)
            try:
                access_token = await self.get_decrypted_token(connection_id)
            except Exception as e:
                logger.error(f"Failed to get token for connection {connection_id}: {e}")
                return GitConnectionStatus(
                    connection_id=connection_id,
                    is_valid=False,
                    username=db_connection.username,
                    scopes=db_connection.scopes or [],
                    last_checked=datetime.now(timezone.utc),
                )

            # Test the token with a simple API call
            is_valid = False
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{api_url}{user_endpoint}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10.0,
                    )
                    is_valid = response.status_code == 200
            except Exception as e:
                logger.error(f"Connection status check failed for {connection_id}: {e}")

            # Update last_used_at only when connection is valid
            if is_valid:
                db_connection.last_used_at = datetime.now(timezone.utc)
                await session.commit()

            return GitConnectionStatus(
                connection_id=connection_id,
                is_valid=is_valid,
                username=db_connection.username,
                scopes=db_connection.scopes or [],
                last_checked=datetime.now(timezone.utc),
            )


# Global service instance
_git_service: Optional[GitService] = None


def get_git_service() -> GitService:
    """Get or create the global git service."""
    global _git_service
    if _git_service is None:
        _git_service = GitService()
    return _git_service
