"""
Tests for Git routes and controller.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.main import app
from app.models.git_models import GitProvider, GitConnection, OAuthInitiateResponse

# Valid PKCE test values (43+ characters, base64url)
TEST_CODE_CHALLENGE = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
TEST_CODE_VERIFIER = "dBjftJeZ4CVP_mB92K27uhbUJU1p1r~wW1gFWFOEjXk"


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestGitRoutes:
    """Test cases for git routes."""

    @patch('app.services.git_service.GitService.initiate_oauth')
    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_github(self, mock_settings, mock_initiate, client):
        """Test initiating OAuth for GitHub."""
        mock_settings.return_value.GITHUB_CLIENT_ID = "test_client_id"
        mock_initiate.return_value = OAuthInitiateResponse(
            authorization_url="https://github.com/login/oauth/authorize?...",
            state="test_state",
        )

        response = client.post(
            "/api/v1/git/oauth/initiate",
            json={
                "provider": "github",
                "code_challenge": TEST_CODE_CHALLENGE,
                "code_challenge_method": "S256",
                "redirect_uri": "pocketclaude://oauth-callback",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        mock_initiate.assert_called_once()

    @patch('app.services.git_service.GitService.initiate_oauth')
    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_gitlab_with_instance_url(
        self, mock_settings, mock_initiate, client
    ):
        """Test initiating OAuth for GitLab with instance URL."""
        mock_settings.return_value.GITLAB_CLIENT_ID = "test_client_id"
        mock_initiate.return_value = OAuthInitiateResponse(
            authorization_url="https://gitlab.com/oauth/authorize?...",
            state="test_state",
        )

        response = client.post(
            "/api/v1/git/oauth/initiate",
            json={
                "provider": "gitlab",
                "instance_url": "https://gitlab.com",
                "code_challenge": TEST_CODE_CHALLENGE,
                "code_challenge_method": "S256",
                "redirect_uri": "pocketclaude://oauth-callback",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data

    def test_initiate_oauth_invalid_provider(self, client):
        """Test initiating OAuth with invalid provider."""
        response = client.post(
            "/api/v1/git/oauth/initiate",
            json={
                "provider": "invalid",
                "code_challenge": TEST_CODE_CHALLENGE,
                "code_challenge_method": "S256",
                "redirect_uri": "pocketclaude://oauth-callback",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_initiate_oauth_missing_required_fields(self, client):
        """Test initiating OAuth with missing required fields."""
        response = client.post(
            "/api/v1/git/oauth/initiate",
            json={
                "provider": "github",
                # Missing code_challenge and redirect_uri
            },
        )

        assert response.status_code == 422  # Validation error

    @patch('app.services.git_service.GitService.handle_oauth_callback')
    @patch('app.services.git_service.get_settings')
    def test_oauth_callback_success(self, mock_settings, mock_callback, client):
        """Test handling OAuth callback successfully."""
        mock_settings.return_value.GITHUB_CLIENT_ID = "test_client_id"
        
        mock_connection = GitConnection(
            id="test_id",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="testuser",
            email="test@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        mock_callback.return_value = mock_connection

        response = client.post(
            "/api/v1/git/oauth/callback",
            json={
                "provider": "github",
                "code": "test_code",
                "state": "test_state",
                "code_verifier": TEST_CODE_VERIFIER,
                "redirect_uri": "pocketclaude://oauth-callback",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test_id"
        assert data["username"] == "testuser"
        assert data["provider"] == "github"
        mock_callback.assert_called_once()

    @patch('app.services.git_service.GitService.list_connections')
    def test_list_connections(self, mock_list, client):
        """Test listing connections."""
        mock_connection = GitConnection(
            id="test_id",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="testuser",
            email="test@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        mock_list.return_value = [mock_connection]

        response = client.get("/api/v1/git/connections")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test_id"
        assert data[0]["username"] == "testuser"

    @patch('app.services.git_service.GitService.get_connection')
    def test_get_connection_success(self, mock_get, client):
        """Test getting a specific connection."""
        mock_connection = GitConnection(
            id="test_id",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="testuser",
            email="test@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        mock_get.return_value = mock_connection

        response = client.get("/api/v1/git/connections/test_id")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_id"
        assert data["username"] == "testuser"

    @patch('app.services.git_service.GitService.get_connection')
    def test_get_connection_not_found(self, mock_get, client):
        """Test getting a connection that doesn't exist."""
        from app.core.exceptions import NotFoundException

        mock_get.side_effect = NotFoundException("Connection not found")

        response = client.get("/api/v1/git/connections/nonexistent")

        assert response.status_code == 404

    @patch('app.services.git_service.GitService.delete_connection')
    def test_delete_connection_success(self, mock_delete, client):
        """Test deleting a connection."""
        mock_delete.return_value = None

        response = client.delete("/api/v1/git/connections/test_id")

        assert response.status_code == 204
        assert response.content == b''  # No content for 204
        mock_delete.assert_called_once_with("test_id")

    @patch('app.services.git_service.GitService.delete_connection')
    def test_delete_connection_not_found(self, mock_delete, client):
        """Test deleting a connection that doesn't exist."""
        from app.core.exceptions import NotFoundException

        mock_delete.side_effect = NotFoundException("Connection not found")

        response = client.delete("/api/v1/git/connections/nonexistent")

        assert response.status_code == 404

    @patch('app.services.git_service.GitService.check_connection_status')
    def test_check_connection_status(self, mock_check, client):
        """Test checking connection status."""
        from app.models.git_models import GitConnectionStatus

        mock_status = GitConnectionStatus(
            connection_id="test_id",
            is_valid=True,
            username="testuser",
            scopes=["repo", "user:email"],
            last_checked=datetime.now(timezone.utc),
        )
        mock_check.return_value = mock_status

        response = client.get("/api/v1/git/connections/test_id/status")

        assert response.status_code == 200
        data = response.json()
        assert data["connection_id"] == "test_id"
        assert data["is_valid"] is True
        assert data["username"] == "testuser"
