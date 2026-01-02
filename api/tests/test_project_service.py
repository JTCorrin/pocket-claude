"""
Tests for ProjectService.
"""
import pytest
from pathlib import Path
import json

from app.services.project_service import ProjectService
from app.utils.path_utils import decode_project_path


class TestProjectService:
    """Test cases for ProjectService."""

    def test_decode_project_path(self):
        """Test decoding project path from folder name."""
        # Test with leading hyphen
        assert (
            decode_project_path("-Users-test-project")
            == "/Users/test/project"
        )

        # Test without leading hyphen
        assert decode_project_path("home-user-code") == "/home/user/code"

    def test_list_projects_empty(self, temp_claude_dir):
        """Test listing projects when none exist."""
        service = ProjectService()
        projects = service.list_projects()

        assert projects == []

    def test_list_projects_with_data(self, temp_claude_dir, create_test_session):
        """Test listing projects with existing data."""
        # Create test session which creates a project
        create_test_session()

        service = ProjectService()
        projects = service.list_projects()

        assert len(projects) == 1
        assert projects[0].path == "/Users/test/project"
        assert projects[0].session_count == 1

    def test_list_projects_multiple_sessions(
        self, temp_claude_dir, create_test_session
    ):
        """Test listing projects with multiple sessions."""
        # Create multiple sessions in same project
        create_test_session(session_id="session-1")
        create_test_session(session_id="session-2")
        create_test_session(session_id="session-3")

        service = ProjectService()
        projects = service.list_projects()

        assert len(projects) == 1
        assert projects[0].session_count == 3

    def test_list_projects_multiple_projects(
        self, temp_claude_dir, create_test_session
    ):
        """Test listing multiple projects."""
        # Create sessions in different projects
        create_test_session(
            session_id="session-1",
            project_encoded="-Users-test-project1",
        )
        create_test_session(
            session_id="session-2",
            project_encoded="-Users-test-project2",
        )

        service = ProjectService()
        projects = service.list_projects()

        assert len(projects) == 2
        project_paths = {p.path for p in projects}
        assert "/Users/test/project1" in project_paths
        assert "/Users/test/project2" in project_paths

    def test_list_projects_sorted_by_date(self, temp_claude_dir):
        """Test that projects are sorted by last_active descending."""
        projects_dir = temp_claude_dir["projects_dir"]

        # Create older project
        project1_dir = projects_dir / "-Users-test-project1"
        project1_dir.mkdir()
        session1_file = project1_dir / "session-1.jsonl"
        with open(session1_file, "w") as f:
            f.write(json.dumps({"type": "test"}) + "\n")

        # Create newer project
        import time

        time.sleep(0.01)  # Ensure different modification times
        project2_dir = projects_dir / "-Users-test-project2"
        project2_dir.mkdir()
        session2_file = project2_dir / "session-2.jsonl"
        with open(session2_file, "w") as f:
            f.write(json.dumps({"type": "test"}) + "\n")

        service = ProjectService()
        projects = service.list_projects()

        assert len(projects) == 2
        # Newer project should be first
        assert projects[0].path == "/Users/test/project2"
        assert projects[1].path == "/Users/test/project1"

    def test_list_projects_no_projects_dir(self, temp_claude_dir):
        """Test listing projects when projects directory doesn't exist."""
        # Remove projects directory
        projects_dir = temp_claude_dir["projects_dir"]
        projects_dir.rmdir()

        service = ProjectService()
        projects = service.list_projects()

        assert projects == []
