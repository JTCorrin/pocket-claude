"""
Pytest configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import json
from datetime import datetime

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def temp_claude_dir(monkeypatch):
    """Create a temporary .claude directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        claude_dir = temp_path / ".claude"
        projects_dir = claude_dir / "projects"
        projects_dir.mkdir(parents=True)

        # Mock the Path.home() method correctly
        def mock_home():
            return temp_path

        monkeypatch.setattr("pathlib.Path.home", mock_home)

        yield {
            "claude_dir": claude_dir,
            "projects_dir": projects_dir,
        }


@pytest.fixture
def sample_session_data():
    """Provide sample session data."""
    return {
        "session_id": "test-session-123",
        "project_path": "/Users/test/project",
        "encoded_project": "-Users-test-project",
        "messages": [
            {
                "type": "user",
                "message": {"role": "user", "content": "Test message 1"},
                "sessionId": "test-session-123",
                "timestamp": "2025-01-02T10:00:00Z",
            },
            {
                "type": "user",
                "message": {"role": "user", "content": "Test message 2"},
                "sessionId": "test-session-123",
                "timestamp": "2025-01-02T10:05:00Z",
            },
        ],
    }


@pytest.fixture
def create_test_session(temp_claude_dir, sample_session_data):
    """Factory fixture to create test sessions."""

    def _create_session(
        session_id=None,
        project_encoded=None,
        messages=None,
    ):
        session_id = session_id or sample_session_data["session_id"]
        project_encoded = project_encoded or sample_session_data["encoded_project"]
        messages = messages or sample_session_data["messages"]

        # Create project directory
        project_dir = temp_claude_dir["projects_dir"] / project_encoded
        project_dir.mkdir(exist_ok=True)

        # Create session file
        session_file = project_dir / f"{session_id}.jsonl"
        with open(session_file, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        return {
            "session_id": session_id,
            "project_dir": project_dir,
            "session_file": session_file,
        }

    return _create_session
