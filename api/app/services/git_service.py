"""
Git provider OAuth and connection management.
"""
import secrets
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx

from app.models.git_models import (
    GitProvider,
    GitConnection,
    GitConnectionStatus,
    OAuthInitiateResponse,
)
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Constants
MAX_ERROR_MESSAGE_LENGTH = 200  # Maximum length for error message snippets
OAUTH_STATE_EXPIRY_MINUTES = 15  # OAuth states expire after 15 minutes


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
    """

    def __init__(self):
        """Initialize git service."""
        # In-memory storage for OAuth states and connections
        # In production, this should be a database
        self._oauth_states: Dict[str, Dict[str, Any]] = {}
        self._connections: Dict[str, GitConnection] = {}
        self._settings = get_settings()
        
        logger.warning(
            "GitService is using in-memory storage for OAuth states and connections. "
            "All OAuth states and connections will be lost if the server restarts or crashes. "
            "This configuration is intended for development only and MUST be replaced with "
            "persistent storage in production."
        )
    
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

        # Store state for verification
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

            if not access_token:
                raise BadRequestException("No access token in response")

            # Get user info
            user_response = await client.get(
                f"{api_url}{user_endpoint}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code != 200:
                raise BadRequestException("Failed to fetch user info")

            user_data = user_response.json()

        # Create connection
        connection_id = secrets.token_urlsafe(16)
        connection = GitConnection(
            id=connection_id,
            provider=provider,
            instance_url=instance_url,
            username=user_data.get("login") or user_data.get("username"),
            email=user_data.get("email"),
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )

        # Store connection (in production, save to database with encrypted tokens)
        # NOTE: In production, you MUST store access_token and refresh_token securely
        # For now, we store connection metadata only
        # TODO: Implement secure token storage with encryption
        self._connections[connection_id] = connection
        
        # Store tokens separately (in production, encrypt these!)
        # This is a placeholder to show where tokens would be stored
        if not hasattr(self, '_tokens'):
            self._tokens: Dict[str, Dict[str, str]] = {}
        self._tokens[connection_id] = {
            "access_token": access_token,
            "refresh_token": refresh_token if refresh_token else "",
        }
        
        logger.warning(
            f"Access token for connection {connection_id} is stored unencrypted in memory. "
            "This is NOT secure and must be replaced with encrypted database storage in production."
        )

        # Clean up OAuth state
        del self._oauth_states[state]

        logger.info(
            f"Created git connection {connection_id} for {provider.value} user {connection.username}"
        )

        return connection

    def get_connection(self, connection_id: str) -> GitConnection:
        """
        Get git connection by ID.

        Args:
            connection_id: Connection identifier

        Returns:
            Git connection

        Raises:
            NotFoundException: If connection not found
        """
        if connection_id not in self._connections:
            raise NotFoundException(f"Connection not found: {connection_id}")

        return self._connections[connection_id]

    def list_connections(self) -> list[GitConnection]:
        """
        List all git connections.

        Returns:
            List of git connections
        """
        return list(self._connections.values())

    def delete_connection(self, connection_id: str) -> None:
        """
        Delete a git connection.

        Args:
            connection_id: Connection identifier

        Raises:
            NotFoundException: If connection not found
        """
        if connection_id not in self._connections:
            raise NotFoundException(f"Connection not found: {connection_id}")

        del self._connections[connection_id]
        logger.info(f"Deleted git connection {connection_id}")

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
        connection = self.get_connection(connection_id)

        # In production, you would:
        # 1. Decrypt the access token
        # 2. Make a test API call to verify it's still valid
        # 3. Return actual scopes and validity

        # For now, return mock status
        return GitConnectionStatus(
            connection_id=connection_id,
            is_valid=True,
            username=connection.username,
            scopes=[],
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
