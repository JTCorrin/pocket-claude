"""
Tests for Claude API endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.models.claude_models import SessionInfo, ProjectInfo


class TestSessionsEndpoint:
    """Test cases for GET /api/v1/sessions endpoint."""

    @patch("app.api.v1.routes.claude_routes.claude_controller.session_service.list_sessions")
    def test_list_sessions_success(self, mock_list_sessions, client):
        """Test listing sessions successfully."""
        # Create mock session
        mock_session = SessionInfo(
            session_id="test-session-123",
            project="/Users/test/project",
            preview="Test message",
            last_active=datetime.now(),
            message_count=2,
        )

        mock_list_sessions.return_value = [mock_session]

        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_id"] == "test-session-123"

    @patch("app.api.v1.routes.claude_routes.claude_controller.session_service.list_sessions")
    def test_list_sessions_with_limit(self, mock_list_sessions, client):
        """Test listing sessions with limit parameter."""
        # Configure mock to return 3 sessions
        mock_sessions = [
            SessionInfo(
                session_id=f"session-{i}",
                project="/Users/test/project",
                preview="Test",
                last_active=datetime.now(),
                message_count=1,
            )
            for i in range(3)
        ]

        mock_list_sessions.return_value = mock_sessions

        response = client.get("/api/v1/sessions?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 3

    @patch("app.api.v1.routes.claude_routes.claude_controller.session_service.list_sessions")
    def test_list_sessions_with_project_filter(self, mock_list_sessions, client):
        """Test listing sessions with project filter."""
        mock_session = SessionInfo(
            session_id="session-1",
            project="/Users/test/project1",
            preview="Test",
            last_active=datetime.now(),
            message_count=1,
        )

        mock_list_sessions.return_value = [mock_session]

        response = client.get("/api/v1/sessions?project=/Users/test/project1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1

    def test_list_sessions_invalid_limit(self, client):
        """Test listing sessions with invalid limit."""
        response = client.get("/api/v1/sessions?limit=200")

        # Should fail validation (max 100)
        assert response.status_code == 422

    @patch("app.api.v1.routes.claude_routes.claude_controller.session_service.list_sessions")
    def test_list_sessions_empty(self, mock_list_sessions, client):
        """Test listing sessions when none exist."""
        mock_list_sessions.return_value = []

        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []


class TestChatEndpoint:
    """Test cases for POST /api/v1/chat endpoint."""

    @patch("app.services.claude_service.subprocess.run")
    def test_chat_success(self, mock_run, client):
        """Test chat endpoint successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response from Claude\nSession: abc-123-def",
            stderr="",
        )

        response = client.post(
            "/api/v1/chat",
            json={"message": "Test message"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["exit_code"] == 0

    @patch("app.services.claude_service.subprocess.run")
    def test_chat_with_session_id(self, mock_run, client):
        """Test chat with session ID."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response",
            stderr="",
        )

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Test message",
                "session_id": "existing-session-123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session-123"

    @patch("app.services.claude_service.subprocess.run")
    def test_chat_with_project_path(self, mock_run, client, temp_claude_dir):
        """Test chat with project path."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response",
            stderr="",
        )

        # Create a temporary project directory
        project_dir = temp_claude_dir["projects_dir"] / "test-project"
        project_dir.mkdir()

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Test message",
                "project_path": str(project_dir),
            },
        )

        assert response.status_code == 200

    def test_chat_empty_message(self, client):
        """Test chat with empty message."""
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
        )

        assert response.status_code == 400

    def test_chat_missing_message(self, client):
        """Test chat without message field."""
        response = client.post(
            "/api/v1/chat",
            json={},
        )

        assert response.status_code == 422  # Validation error

    @patch("app.services.claude_service.subprocess.run")
    def test_chat_with_permissions_skip(self, mock_run, client):
        """Test chat with dangerously_skip_permissions."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Response",
            stderr="",
        )

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Test message",
                "dangerously_skip_permissions": True,
            },
        )

        assert response.status_code == 200


class TestHealthEndpoint:
    """Test cases for GET /api/v1/health endpoint."""

    @patch("app.services.claude_service.subprocess.run")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_health_check_success(self, mock_run, client):
        """Test health check endpoint successfully."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="claude 2.0.76\n",
            stderr="",
        )

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["claude_version"] == "2.0.76"
        assert data["api_key_configured"] is True

    @patch("app.services.claude_service.subprocess.run")
    @patch.dict("os.environ", {}, clear=True)
    def test_health_check_no_api_key(self, mock_run, client):
        """Test health check when API key is not configured."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="claude 2.0.76\n",
            stderr="",
        )

        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["api_key_configured"] is False

    @patch("app.services.claude_service.subprocess.run")
    def test_health_check_claude_not_found(self, mock_run, client):
        """Test health check when Claude CLI is not found."""
        mock_run.side_effect = FileNotFoundError()

        response = client.get("/api/v1/health")

        assert response.status_code == 503  # Service Unavailable
        assert "error" in response.json()
        error = response.json()["error"]
        assert error["type"] == "CLINotFoundException"
        assert "Claude CLI not found" in error["message"]


class TestProjectsEndpoint:
    """Test cases for GET /api/v1/projects endpoint."""

    @patch("app.api.v1.routes.claude_routes.claude_controller.project_service.list_projects")
    def test_list_projects_success(self, mock_list_projects, client):
        """Test listing projects successfully."""
        mock_project = ProjectInfo(
            path="/Users/test/project",
            session_count=1,
            last_active=datetime.now(),
        )

        mock_list_projects.return_value = [mock_project]

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert len(data["projects"]) == 1
        assert data["projects"][0]["path"] == "/Users/test/project"
        assert data["projects"][0]["session_count"] == 1

    @patch("app.api.v1.routes.claude_routes.claude_controller.project_service.list_projects")
    def test_list_projects_multiple(self, mock_list_projects, client):
        """Test listing multiple projects."""
        mock_projects = [
            ProjectInfo(
                path="/Users/test/project1",
                session_count=1,
                last_active=datetime.now(),
            ),
            ProjectInfo(
                path="/Users/test/project2",
                session_count=1,
                last_active=datetime.now(),
            ),
        ]

        mock_list_projects.return_value = mock_projects

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 2

    @patch("app.api.v1.routes.claude_routes.claude_controller.project_service.list_projects")
    def test_list_projects_empty(self, mock_list_projects, client):
        """Test listing projects when none exist."""
        mock_list_projects.return_value = []

        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert data["projects"] == []


class TestRootEndpoints:
    """Test cases for root-level endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data

    def test_app_health_endpoint(self, client):
        """Test application-level health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
