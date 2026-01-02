"""
Tests for ClaudeService.
"""
import pytest
from unittest.mock import patch, MagicMock
import subprocess

from app.services.claude_service import ClaudeService
from app.core.exceptions import AppException, BadRequestException


class TestClaudeService:
    """Test cases for ClaudeService."""

    def test_init(self):
        """Test service initialization."""
        service = ClaudeService()
        assert service.timeout == 300

    @patch("subprocess.run")
    def test_get_version_success(self, mock_run):
        """Test getting Claude version successfully."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="claude 2.0.76\n", stderr=""
        )

        service = ClaudeService()
        version = service.get_version()

        assert version == "2.0.76"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_get_version_not_found(self, mock_run):
        """Test getting version when Claude CLI is not found."""
        mock_run.side_effect = FileNotFoundError()

        service = ClaudeService()
        with pytest.raises(AppException, match="Claude CLI not found"):
            service.get_version()

    @patch("subprocess.run")
    def test_get_version_timeout(self, mock_run):
        """Test getting version when command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 10)

        service = ClaudeService()
        with pytest.raises(AppException, match="timed out"):
            service.get_version()

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_check_api_key_configured(self):
        """Test checking API key when it is configured."""
        service = ClaudeService()
        assert service.check_api_key() is True

    @patch.dict("os.environ", {}, clear=True)
    def test_check_api_key_not_configured(self):
        """Test checking API key when it is not configured."""
        service = ClaudeService()
        assert service.check_api_key() is False

    @patch("subprocess.run")
    def test_execute_chat_success(self, mock_run):
        """Test executing chat successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response from Claude\nSession: abc-123",
            stderr="",
        )

        service = ClaudeService()
        response, session_id, exit_code, stderr = service.execute_chat(
            message="Test message"
        )

        assert "Response from Claude" in response
        assert exit_code == 0
        assert stderr == ""
        # Check that command was called correctly
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "claude"
        assert call_args[1] == "-p"
        assert call_args[2] == "Test message"

    @patch("subprocess.run")
    def test_execute_chat_with_session_id(self, mock_run):
        """Test executing chat with session ID."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response",
            stderr="",
        )

        service = ClaudeService()
        service.execute_chat(
            message="Test",
            session_id="abc-123",
        )

        call_args = mock_run.call_args[0][0]
        assert "--resume" in call_args
        assert "abc-123" in call_args

    @patch("subprocess.run")
    def test_execute_chat_with_permissions_skip(self, mock_run):
        """Test executing chat with permissions skip."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response",
            stderr="",
        )

        service = ClaudeService()
        service.execute_chat(
            message="Test",
            dangerously_skip_permissions=True,
        )

        call_args = mock_run.call_args[0][0]
        assert "--dangerously-skip-permissions" in call_args

    def test_execute_chat_empty_message(self):
        """Test executing chat with empty message."""
        service = ClaudeService()
        with pytest.raises(BadRequestException, match="Message cannot be empty"):
            service.execute_chat(message="")

    @patch("os.path.exists")
    def test_execute_chat_invalid_project_path(self, mock_exists):
        """Test executing chat with non-existent project path."""
        mock_exists.return_value = False

        service = ClaudeService()
        with pytest.raises(BadRequestException, match="does not exist"):
            service.execute_chat(
                message="Test",
                project_path="/non/existent/path",
            )

    @patch("subprocess.run")
    def test_execute_chat_timeout(self, mock_run):
        """Test executing chat when command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 300)

        service = ClaudeService()
        with pytest.raises(AppException, match="timed out"):
            service.execute_chat(message="Test message")

    @patch("subprocess.run")
    def test_execute_chat_cli_not_found(self, mock_run):
        """Test executing chat when CLI is not found."""
        mock_run.side_effect = FileNotFoundError()

        service = ClaudeService()
        with pytest.raises(AppException, match="Claude CLI not found"):
            service.execute_chat(message="Test message")
