"""
Tests for SessionService.
"""
import pytest
import json

from app.services.session_service import SessionService
from app.core.exceptions import NotFoundException
from app.utils.path_utils import decode_project_path


class TestSessionService:
    """Test cases for SessionService."""

    def test_decode_project_path(self):
        """Test decoding project path from folder name."""
        # Test with leading hyphen
        assert (
            decode_project_path("-Users-test-project")
            == "/Users/test/project"
        )

        # Test without leading hyphen
        assert decode_project_path("home-user-code") == "/home/user/code"

    def test_list_sessions_empty(self, temp_claude_dir):
        """Test listing sessions when none exist."""
        service = SessionService()
        sessions = service.list_sessions()

        assert sessions == []

    def test_list_sessions_with_data(self, temp_claude_dir, create_test_session):
        """Test listing sessions with existing data."""
        # Create test session
        create_test_session()

        service = SessionService()
        sessions = service.list_sessions()

        assert len(sessions) == 1
        assert sessions[0].session_id == "test-session-123"
        assert sessions[0].project == "/Users/test/project"
        assert sessions[0].preview == "Test message 1"
        assert sessions[0].message_count == 2

    def test_list_sessions_multiple_projects(
        self, temp_claude_dir, create_test_session, sample_session_data
    ):
        """Test listing sessions from multiple projects."""
        # Create sessions in different projects
        create_test_session(
            session_id="session-1",
            project_encoded="-Users-test-project1",
        )
        create_test_session(
            session_id="session-2",
            project_encoded="-Users-test-project2",
        )

        service = SessionService()
        sessions = service.list_sessions()

        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert "session-1" in session_ids
        assert "session-2" in session_ids

    def test_list_sessions_with_limit(self, temp_claude_dir, create_test_session):
        """Test listing sessions with limit."""
        # Create multiple sessions
        for i in range(5):
            create_test_session(
                session_id=f"session-{i}",
            )

        service = SessionService()
        sessions = service.list_sessions(limit=3)

        assert len(sessions) == 3

    def test_list_sessions_with_project_filter(
        self, temp_claude_dir, create_test_session
    ):
        """Test listing sessions with project filter."""
        create_test_session(
            session_id="session-1",
            project_encoded="-Users-test-project1",
        )
        create_test_session(
            session_id="session-2",
            project_encoded="-Users-test-project2",
        )

        service = SessionService()
        sessions = service.list_sessions(project="/Users/test/project1")

        assert len(sessions) == 1
        assert sessions[0].session_id == "session-1"

    def test_list_sessions_sorted_by_date(self, temp_claude_dir, sample_session_data):
        """Test that sessions are sorted by last_active descending."""
        projects_dir = temp_claude_dir["projects_dir"]

        # Create sessions with different timestamps
        project_dir = projects_dir / "-Users-test-project"
        project_dir.mkdir(exist_ok=True)

        # Older session
        session1_file = project_dir / "session-old.jsonl"
        with open(session1_file, "w") as f:
            msg = {
                "type": "user",
                "message": {"content": "Old message"},
                "timestamp": "2025-01-01T10:00:00Z",
            }
            f.write(json.dumps(msg) + "\n")

        # Newer session
        session2_file = project_dir / "session-new.jsonl"
        with open(session2_file, "w") as f:
            msg = {
                "type": "user",
                "message": {"content": "New message"},
                "timestamp": "2025-01-02T10:00:00Z",
            }
            f.write(json.dumps(msg) + "\n")

        service = SessionService()
        sessions = service.list_sessions()

        assert len(sessions) == 2
        # Newer session should be first
        assert sessions[0].session_id == "session-new"
        assert sessions[1].session_id == "session-old"

    def test_get_session_success(self, temp_claude_dir, create_test_session):
        """Test getting a specific session."""
        create_test_session()

        service = SessionService()
        session = service.get_session("test-session-123")

        assert session.session_id == "test-session-123"
        assert session.project == "/Users/test/project"
        assert session.preview == "Test message 1"

    def test_get_session_not_found(self, temp_claude_dir):
        """Test getting a non-existent session."""
        service = SessionService()

        with pytest.raises(NotFoundException, match="Session not found"):
            service.get_session("non-existent-session")

    def test_parse_session_file_with_preview_truncation(
        self, temp_claude_dir, sample_session_data
    ):
        """Test that long previews are truncated."""
        projects_dir = temp_claude_dir["projects_dir"]
        project_dir = projects_dir / "-Users-test-project"
        project_dir.mkdir(exist_ok=True)

        # Create session with very long message
        session_file = project_dir / "test-session.jsonl"
        long_message = "A" * 200  # 200 character message
        with open(session_file, "w") as f:
            msg = {
                "type": "user",
                "message": {"content": long_message},
                "timestamp": "2025-01-02T10:00:00Z",
            }
            f.write(json.dumps(msg) + "\n")

        service = SessionService()
        session_info = service._parse_session_file(session_file)

        assert len(session_info.preview) == 100
        assert session_info.preview.endswith("...")

    def test_parse_session_file_no_messages(self, temp_claude_dir):
        """Test parsing session file with no user messages."""
        projects_dir = temp_claude_dir["projects_dir"]
        project_dir = projects_dir / "-Users-test-project"
        project_dir.mkdir(exist_ok=True)

        session_file = project_dir / "test-session.jsonl"
        with open(session_file, "w") as f:
            # Write non-user entry
            msg = {"type": "other", "data": "test"}
            f.write(json.dumps(msg) + "\n")

        service = SessionService()
        session_info = service._parse_session_file(session_file)

        assert session_info.preview == "No messages"
        assert session_info.message_count == 0
