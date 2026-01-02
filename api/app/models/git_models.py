"""
Git provider connection models.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GitProvider(str, Enum):
    """Supported git providers."""

    GITHUB = "github"
    GITLAB = "gitlab"
    GITEA = "gitea"


class GitConnectionCreate(BaseModel):
    """Request to create a git connection."""

    provider: GitProvider
    instance_url: Optional[str] = Field(
        None,
        description="Custom instance URL for self-hosted GitLab/Gitea",
    )


class OAuthInitiateRequest(BaseModel):
    """Request to initiate OAuth flow."""

    provider: GitProvider
    instance_url: Optional[str] = None
    code_challenge: str = Field(
        ...,
        min_length=43,
        max_length=128,
        description="PKCE code challenge",
    )
    code_challenge_method: str = Field(
        default="S256", description="Challenge method (S256 or plain)"
    )
    redirect_uri: str = Field(..., description="OAuth redirect URI")


class OAuthInitiateResponse(BaseModel):
    """Response with OAuth authorization URL."""

    authorization_url: str
    state: str = Field(..., description="OAuth state for CSRF protection")


class OAuthCallbackRequest(BaseModel):
    """OAuth callback data."""

    provider: GitProvider
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="OAuth state for verification")
    code_verifier: str = Field(
        ..., min_length=43, max_length=128, description="PKCE code verifier"
    )
    redirect_uri: str


class GitConnection(BaseModel):
    """Git provider connection."""

    id: str
    provider: GitProvider
    instance_url: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class GitConnectionStatus(BaseModel):
    """Git connection status check."""

    connection_id: str
    is_valid: bool
    username: Optional[str] = None
    scopes: list[str] = []
    last_checked: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
