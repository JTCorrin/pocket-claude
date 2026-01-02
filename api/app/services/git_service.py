"""
Git provider OAuth and connection management.
"""
import secrets
import hashlib
import base64
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

from app.models.git_models import (
    GitProvider,
    GitConnection,
    GitConnectionStatus,
    OAuthInitiateResponse,
)
from app.core.exceptions import BadRequestException, NotFoundException

logger = logging.getLogger(__name__)


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
        # Validate instance URL for self-hosted providers
        if provider in (GitProvider.GITLAB, GitProvider.GITEA):
            if not instance_url:
                raise BadRequestException(
                    f"{provider.value} requires instance_url for self-hosted instances"
                )

        # Generate secure random state for CSRF protection
        state = secrets.token_urlsafe(32)

        # Get provider configuration
        if provider == GitProvider.GITHUB:
            config = GitProviderConfig.GITHUB
            auth_url = config["auth_url"]
            scopes = config["scopes"]
        elif provider == GitProvider.GITLAB:
            config = GitProviderConfig.GITLAB
            auth_url = config["auth_url_template"].format(instance=instance_url)
            scopes = config["scopes"]
        else:  # GITEA
            config = GitProviderConfig.GITEA
            auth_url = config["auth_url_template"].format(instance=instance_url)
            scopes = config["scopes"]

        # Build authorization URL with PKCE parameters
        params = {
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        }

        # GitHub/GitLab/Gitea may require client_id, but for PKCE flow
        # we're using a public client pattern. In production, you'd need to
        # register an OAuth app and provide client_id here.
        # For now, this is a template showing the flow.

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
        # Verify state
        if state not in self._oauth_states:
            raise NotFoundException(f"OAuth state not found: {state}")

        oauth_data = self._oauth_states[state]

        # Verify provider matches
        if oauth_data["provider"] != provider.value:
            raise BadRequestException("Provider mismatch")

        # Verify redirect URI
        if oauth_data["redirect_uri"] != redirect_uri:
            raise BadRequestException("Redirect URI mismatch")

        instance_url = oauth_data.get("instance_url")

        # Get provider configuration
        if provider == GitProvider.GITHUB:
            config = GitProviderConfig.GITHUB
            token_url = config["token_url"]
            api_url = config["api_url"]
            user_endpoint = config["user_endpoint"]
        elif provider == GitProvider.GITLAB:
            config = GitProviderConfig.GITLAB
            token_url = config["token_url_template"].format(instance=instance_url)
            api_url = config["api_url_template"].format(instance=instance_url)
            user_endpoint = config["user_endpoint"]
        else:  # GITEA
            config = GitProviderConfig.GITEA
            token_url = config["token_url_template"].format(instance=instance_url)
            api_url = config["api_url_template"].format(instance=instance_url)
            user_endpoint = config["user_endpoint"]

        # Exchange code for token using PKCE
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                    # NOTE: In production, you'd need client_id from registered OAuth app
                    # "client_id": settings.GITHUB_CLIENT_ID,
                },
                headers={"Accept": "application/json"},
            )

            if token_response.status_code != 200:
                logger.error(
                    f"Token exchange failed: {token_response.status_code} - {token_response.text}"
                )
                raise BadRequestException("Failed to exchange code for token")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

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
        self._connections[connection_id] = connection

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
