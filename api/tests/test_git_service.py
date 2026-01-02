"""
Tests for GitService.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.git_service import GitService, GitProviderConfig
from app.models.git_models import GitProvider, GitConnection
from app.core.exceptions import BadRequestException, NotFoundException


class TestGitService:
    """Test cases for GitService."""

    def test_init(self):
        """Test service initialization."""
        with patch('app.services.git_service.logger') as mock_logger:
            service = GitService()
            assert service._oauth_states == {}
            assert service._connections == {}
            # Verify warning was logged about in-memory storage
            mock_logger.warning.assert_called_once()
            assert "in-memory storage" in mock_logger.warning.call_args[0][0].lower()

    def test_validate_pkce_parameter_valid(self):
        """Test PKCE parameter validation with valid input."""
        service = GitService()
        # Should not raise for valid base64url characters
        service._validate_pkce_parameter("abc123-_~XYZ", "test_param")

    def test_validate_pkce_parameter_invalid(self):
        """Test PKCE parameter validation with invalid characters."""
        service = GitService()
        # Should raise for invalid characters
        with pytest.raises(BadRequestException, match="base64url characters"):
            service._validate_pkce_parameter("abc+123/xyz=", "test_param")

    def test_validate_instance_url_valid_https(self):
        """Test instance URL validation with valid HTTPS URL."""
        service = GitService()
        service._validate_instance_url("https://gitlab.example.com")
        service._validate_instance_url("https://gitlab.com:443")
        service._validate_instance_url("https://gitlab.com:8443/path")

    def test_validate_instance_url_http_rejected(self):
        """Test instance URL validation rejects HTTP URLs."""
        service = GitService()
        with pytest.raises(BadRequestException, match="HTTPS"):
            service._validate_instance_url("http://gitlab.example.com")

    def test_validate_instance_url_invalid_format(self):
        """Test instance URL validation with invalid format."""
        service = GitService()
        with pytest.raises(BadRequestException, match="Invalid instance URL"):
            service._validate_instance_url("https://")

    def test_cleanup_expired_oauth_states(self):
        """Test OAuth state cleanup removes expired states."""
        service = GitService()
        
        # Add fresh state
        fresh_state = "fresh_state"
        service._oauth_states[fresh_state] = {
            "provider": "github",
            "created_at": datetime.now(timezone.utc),
        }
        
        # Add expired state (20 minutes old)
        expired_state = "expired_state"
        service._oauth_states[expired_state] = {
            "provider": "github",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=20),
        }
        
        service._cleanup_expired_oauth_states()
        
        assert fresh_state in service._oauth_states
        assert expired_state not in service._oauth_states

    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_github_success(self, mock_settings):
        """Test initiating OAuth for GitHub."""
        mock_settings.return_value.GITHUB_CLIENT_ID = "test_client_id"
        
        service = GitService()
        response = service.initiate_oauth(
            provider=GitProvider.GITHUB,
            code_challenge="abc123-_xyz",
            code_challenge_method="S256",
            redirect_uri="pocketclaude://oauth-callback",
        )
        
        assert response.authorization_url.startswith(GitProviderConfig.GITHUB["auth_url"])
        assert "client_id=test_client_id" in response.authorization_url
        assert "code_challenge=abc123-_xyz" in response.authorization_url
        assert response.state is not None
        assert response.state in service._oauth_states

    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_github_no_client_id(self, mock_settings):
        """Test initiating OAuth for GitHub without client_id logs warning."""
        mock_settings.return_value.GITHUB_CLIENT_ID = None
        
        with patch('app.services.git_service.logger') as mock_logger:
            service = GitService()
            response = service.initiate_oauth(
                provider=GitProvider.GITHUB,
                code_challenge="abc123-_xyz",
                code_challenge_method="S256",
                redirect_uri="pocketclaude://oauth-callback",
            )
            
            # Should still work but log warning
            assert response.authorization_url is not None
            # Check warning was logged
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if "No client_id configured" in str(call)]
            assert len(warning_calls) > 0

    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_gitlab_requires_instance_url(self, mock_settings):
        """Test initiating OAuth for GitLab requires instance_url."""
        mock_settings.return_value.GITLAB_CLIENT_ID = "test_client_id"
        
        service = GitService()
        with pytest.raises(BadRequestException, match="instance_url"):
            service.initiate_oauth(
                provider=GitProvider.GITLAB,
                code_challenge="abc123-_xyz",
                code_challenge_method="S256",
                redirect_uri="pocketclaude://oauth-callback",
            )

    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_gitlab_validates_https(self, mock_settings):
        """Test initiating OAuth for GitLab validates HTTPS URL."""
        mock_settings.return_value.GITLAB_CLIENT_ID = "test_client_id"
        
        service = GitService()
        with pytest.raises(BadRequestException, match="HTTPS"):
            service.initiate_oauth(
                provider=GitProvider.GITLAB,
                code_challenge="abc123-_xyz",
                code_challenge_method="S256",
                redirect_uri="pocketclaude://oauth-callback",
                instance_url="http://gitlab.example.com",
            )

    @patch('app.services.git_service.get_settings')
    def test_initiate_oauth_validates_pkce_params(self, mock_settings):
        """Test initiating OAuth validates PKCE parameters."""
        mock_settings.return_value.GITHUB_CLIENT_ID = "test_client_id"
        
        service = GitService()
        with pytest.raises(BadRequestException, match="base64url"):
            service.initiate_oauth(
                provider=GitProvider.GITHUB,
                code_challenge="invalid+chars/here=",
                code_challenge_method="S256",
                redirect_uri="pocketclaude://oauth-callback",
            )

    @pytest.mark.asyncio
    @patch('app.services.git_service.get_settings')
    @patch('httpx.AsyncClient')
    async def test_handle_oauth_callback_success(self, mock_client_class, mock_settings):
        """Test handling OAuth callback successfully."""
        mock_settings.return_value.GITHUB_CLIENT_ID = "test_client_id"
        
        # Mock HTTP responses
        mock_token_response = MagicMock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
        }
        
        mock_user_response = MagicMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = {
            "login": "testuser",
            "email": "test@example.com",
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_response
        mock_client.get.return_value = mock_user_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client
        
        service = GitService()
        
        # Set up OAuth state
        state = "test_state"
        service._oauth_states[state] = {
            "provider": "github",
            "instance_url": None,
            "redirect_uri": "pocketclaude://oauth-callback",
            "created_at": datetime.now(timezone.utc),
        }
        
        connection = await service.handle_oauth_callback(
            provider=GitProvider.GITHUB,
            code="test_code",
            state=state,
            code_verifier="test_verifier",
            redirect_uri="pocketclaude://oauth-callback",
        )
        
        assert connection.username == "testuser"
        assert connection.email == "test@example.com"
        assert connection.provider == GitProvider.GITHUB
        assert connection.is_active is True
        assert state not in service._oauth_states  # State should be cleaned up
        assert connection.id in service._connections

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_state_not_found(self):
        """Test handling OAuth callback with invalid state."""
        service = GitService()
        
        with pytest.raises(NotFoundException, match="OAuth state not found"):
            await service.handle_oauth_callback(
                provider=GitProvider.GITHUB,
                code="test_code",
                state="nonexistent_state",
                code_verifier="test_verifier",
                redirect_uri="pocketclaude://oauth-callback",
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_provider_mismatch(self):
        """Test handling OAuth callback with provider mismatch."""
        service = GitService()
        
        state = "test_state"
        service._oauth_states[state] = {
            "provider": "github",
            "instance_url": None,
            "redirect_uri": "pocketclaude://oauth-callback",
            "created_at": datetime.now(timezone.utc),
        }
        
        with pytest.raises(BadRequestException, match="Provider mismatch"):
            await service.handle_oauth_callback(
                provider=GitProvider.GITLAB,
                code="test_code",
                state=state,
                code_verifier="test_verifier",
                redirect_uri="pocketclaude://oauth-callback",
            )

    @pytest.mark.asyncio
    async def test_handle_oauth_callback_redirect_uri_mismatch(self):
        """Test handling OAuth callback with redirect URI mismatch."""
        service = GitService()
        
        state = "test_state"
        service._oauth_states[state] = {
            "provider": "github",
            "instance_url": None,
            "redirect_uri": "pocketclaude://oauth-callback",
            "created_at": datetime.now(timezone.utc),
        }
        
        with pytest.raises(BadRequestException, match="Redirect URI mismatch"):
            await service.handle_oauth_callback(
                provider=GitProvider.GITHUB,
                code="test_code",
                state=state,
                code_verifier="test_verifier",
                redirect_uri="different://callback",
            )

    @pytest.mark.asyncio
    @patch('app.services.git_service.get_settings')
    @patch('httpx.AsyncClient')
    async def test_handle_oauth_callback_token_exchange_failure(
        self, mock_client_class, mock_settings
    ):
        """Test handling OAuth callback when token exchange fails."""
        mock_settings.return_value.GITHUB_CLIENT_ID = "test_client_id"
        
        # Mock failed token response
        mock_token_response = MagicMock()
        mock_token_response.status_code = 400
        mock_token_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code has expired",
        }
        mock_token_response.text = '{"error":"invalid_grant"}'
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client
        
        service = GitService()
        
        state = "test_state"
        service._oauth_states[state] = {
            "provider": "github",
            "instance_url": None,
            "redirect_uri": "pocketclaude://oauth-callback",
            "created_at": datetime.now(timezone.utc),
        }
        
        with pytest.raises(BadRequestException, match="Token exchange failed"):
            await service.handle_oauth_callback(
                provider=GitProvider.GITHUB,
                code="test_code",
                state=state,
                code_verifier="test_verifier",
                redirect_uri="pocketclaude://oauth-callback",
            )

    def test_get_connection_success(self):
        """Test getting a connection by ID."""
        service = GitService()
        
        connection = GitConnection(
            id="test_id",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="testuser",
            email="test@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        service._connections["test_id"] = connection
        
        result = service.get_connection("test_id")
        assert result == connection

    def test_get_connection_not_found(self):
        """Test getting a connection that doesn't exist."""
        service = GitService()
        
        with pytest.raises(NotFoundException, match="Connection not found"):
            service.get_connection("nonexistent_id")

    def test_list_connections(self):
        """Test listing all connections."""
        service = GitService()
        
        connection1 = GitConnection(
            id="test_id_1",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="user1",
            email="user1@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        connection2 = GitConnection(
            id="test_id_2",
            provider=GitProvider.GITLAB,
            instance_url="https://gitlab.com",
            username="user2",
            email="user2@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        
        service._connections["test_id_1"] = connection1
        service._connections["test_id_2"] = connection2
        
        connections = service.list_connections()
        assert len(connections) == 2
        assert connection1 in connections
        assert connection2 in connections

    def test_delete_connection_success(self):
        """Test deleting a connection."""
        service = GitService()
        
        connection = GitConnection(
            id="test_id",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="testuser",
            email="test@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        service._connections["test_id"] = connection
        
        service.delete_connection("test_id")
        assert "test_id" not in service._connections

    def test_delete_connection_not_found(self):
        """Test deleting a connection that doesn't exist."""
        service = GitService()
        
        with pytest.raises(NotFoundException, match="Connection not found"):
            service.delete_connection("nonexistent_id")

    @pytest.mark.asyncio
    async def test_check_connection_status(self):
        """Test checking connection status."""
        service = GitService()
        
        connection = GitConnection(
            id="test_id",
            provider=GitProvider.GITHUB,
            instance_url=None,
            username="testuser",
            email="test@example.com",
            connected_at=datetime.now(timezone.utc),
            is_active=True,
        )
        service._connections["test_id"] = connection
        
        status = await service.check_connection_status("test_id")
        assert status.connection_id == "test_id"
        assert status.is_valid is True
        assert status.username == "testuser"
