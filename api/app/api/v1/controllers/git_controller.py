"""
Git settings controller.
"""
import logging
from typing import Optional

from app.models.git_models import (
    GitProvider,
    GitConnection,
    GitConnectionStatus,
    OAuthInitiateRequest,
    OAuthInitiateResponse,
    OAuthCallbackRequest,
)
from app.services.git_service import get_git_service

logger = logging.getLogger(__name__)


class GitController:
    """Controller for git provider settings and OAuth."""

    def __init__(self):
        """Initialize git controller."""
        self.git_service = get_git_service()

    def initiate_oauth(
        self, request: OAuthInitiateRequest
    ) -> OAuthInitiateResponse:
        """
        Initiate OAuth flow with PKCE.

        Args:
            request: OAuth initiation request

        Returns:
            Authorization URL and state
        """
        logger.info(f"Initiating OAuth for provider: {request.provider}")

        return self.git_service.initiate_oauth(
            provider=request.provider,
            code_challenge=request.code_challenge,
            code_challenge_method=request.code_challenge_method,
            redirect_uri=request.redirect_uri,
            instance_url=request.instance_url,
        )

    async def handle_oauth_callback(
        self, request: OAuthCallbackRequest
    ) -> GitConnection:
        """
        Handle OAuth callback and create connection.

        Args:
            request: OAuth callback data

        Returns:
            Created git connection
        """
        logger.info(f"Handling OAuth callback for provider: {request.provider}")

        return await self.git_service.handle_oauth_callback(
            provider=request.provider,
            code=request.code,
            state=request.state,
            code_verifier=request.code_verifier,
            redirect_uri=request.redirect_uri,
        )

    def list_connections(self) -> list[GitConnection]:
        """
        List all git connections.

        Returns:
            List of git connections
        """
        connections = self.git_service.list_connections()
        logger.info(f"Listed {len(connections)} git connections")
        return connections

    def get_connection(self, connection_id: str) -> GitConnection:
        """
        Get a specific git connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Git connection
        """
        return self.git_service.get_connection(connection_id)

    def delete_connection(self, connection_id: str) -> dict:
        """
        Delete a git connection.

        Args:
            connection_id: Connection identifier

        Returns:
            Success message
        """
        self.git_service.delete_connection(connection_id)
        logger.info(f"Deleted git connection: {connection_id}")
        return {"message": "Connection deleted successfully"}

    async def check_connection_status(
        self, connection_id: str
    ) -> GitConnectionStatus:
        """
        Check git connection status.

        Args:
            connection_id: Connection identifier

        Returns:
            Connection status
        """
        return await self.git_service.check_connection_status(connection_id)
