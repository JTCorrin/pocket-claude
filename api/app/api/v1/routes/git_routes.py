"""
Git provider settings and OAuth routes.
"""
from fastapi import APIRouter, status
from typing import List

from app.models.git_models import (
    GitConnection,
    GitConnectionStatus,
    OAuthInitiateRequest,
    OAuthInitiateResponse,
    OAuthCallbackRequest,
)
from app.api.v1.controllers.git_controller import GitController

# Create router
router = APIRouter(prefix="/git", tags=["Git Settings"])

# Create controller instance
git_controller = GitController()


@router.post(
    "/oauth/initiate",
    response_model=OAuthInitiateResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate OAuth flow",
    description="""
    Initiate OAuth 2.0 authorization flow with PKCE for git providers.

    This endpoint generates the authorization URL that the client should
    open in a browser/webview. The client must generate a code_verifier
    and compute the code_challenge before calling this endpoint.

    PKCE Flow:
    1. Client generates random code_verifier (43-128 chars)
    2. Client computes code_challenge = BASE64URL(SHA256(code_verifier))
    3. Client calls this endpoint with code_challenge
    4. Client opens returned authorization_url in browser
    5. User authorizes the application
    6. Provider redirects to redirect_uri with authorization code
    7. Client calls /oauth/callback with code and code_verifier

    Supported providers:
    - GitHub: No instance_url needed
    - GitLab: Requires instance_url for self-hosted
    - Gitea: Requires instance_url for self-hosted
    """,
)
async def initiate_oauth(request: OAuthInitiateRequest) -> OAuthInitiateResponse:
    """Initiate OAuth flow with PKCE."""
    return git_controller.initiate_oauth(request)


@router.post(
    "/oauth/callback",
    response_model=GitConnection,
    status_code=status.HTTP_201_CREATED,
    summary="Handle OAuth callback",
    description="""
    Handle OAuth callback and exchange authorization code for access token.

    This endpoint completes the OAuth flow by:
    1. Verifying the OAuth state for CSRF protection
    2. Exchanging the authorization code for an access token using PKCE
    3. Fetching user information from the git provider
    4. Creating and storing the git connection

    The client must provide the same code_verifier used to generate
    the code_challenge in the initiate step.
    """,
)
async def oauth_callback(request: OAuthCallbackRequest) -> GitConnection:
    """Handle OAuth callback."""
    return await git_controller.handle_oauth_callback(request)


@router.get(
    "/connections",
    response_model=List[GitConnection],
    status_code=status.HTTP_200_OK,
    summary="List git connections",
    description="Get all configured git provider connections for the current user.",
)
async def list_connections() -> List[GitConnection]:
    """List all git connections."""
    return await git_controller.list_connections()


@router.get(
    "/connections/{connection_id}",
    response_model=GitConnection,
    status_code=status.HTTP_200_OK,
    summary="Get git connection",
    description="Get details of a specific git connection by ID.",
)
async def get_connection(connection_id: str) -> GitConnection:
    """Get a specific git connection."""
    return await git_controller.get_connection(connection_id)


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete git connection",
    description="Remove a git provider connection. This revokes access and deletes stored credentials.",
)
async def delete_connection(connection_id: str) -> None:
    """Delete a git connection."""
    await git_controller.delete_connection(connection_id)


@router.get(
    "/connections/{connection_id}/status",
    response_model=GitConnectionStatus,
    status_code=status.HTTP_200_OK,
    summary="Check connection status",
    description="""
    Check if a git connection is still valid by making a test API call.

    Returns the connection validity, username, available scopes, and
    when the check was performed.
    """,
)
async def check_connection_status(connection_id: str) -> GitConnectionStatus:
    """Check if a git connection is still valid."""
    return await git_controller.check_connection_status(connection_id)
