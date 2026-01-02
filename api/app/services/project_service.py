"""
Service for managing Claude Code projects.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from app.models.claude_models import ProjectInfo
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


class ProjectService:
    """Service for managing Claude Code projects."""

    def __init__(self):
        """Initialize the project service."""
        self.claude_dir = Path.home() / ".claude"
        self.projects_dir = self.claude_dir / "projects"

    def _decode_project_path(self, folder_name: str) -> str:
        """
        Decode a project folder name to its original path.

        Args:
            folder_name: The encoded folder name

        Returns:
            The decoded project path
        """
        # Remove leading hyphen if present and replace hyphens with slashes
        if folder_name.startswith("-"):
            folder_name = folder_name[1:]
        return "/" + folder_name.replace("-", "/")

    def list_projects(self) -> list[ProjectInfo]:
        """
        List all known Claude Code projects.

        Returns:
            List of ProjectInfo objects

        Raises:
            AppException: If unable to read projects
        """
        try:
            if not self.projects_dir.exists():
                logger.warning(f"Projects directory does not exist: {self.projects_dir}")
                return []

            projects = []

            # Iterate through project directories
            for project_dir in self.projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                # Decode project path
                project_path = self._decode_project_path(project_dir.name)

                # Count session files
                session_files = list(project_dir.glob("*.jsonl"))
                session_count = len(session_files)

                # Get last active time from most recent session file
                last_active = None
                for session_file in session_files:
                    file_time = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
                    if last_active is None or file_time > last_active:
                        last_active = file_time

                # Use directory modification time if no sessions
                if last_active is None:
                    last_active = datetime.fromtimestamp(project_dir.stat().st_mtime, tz=timezone.utc)

                projects.append(
                    ProjectInfo(
                        path=project_path,
                        session_count=session_count,
                        last_active=last_active,
                    )
                )

            # Sort by last_active descending
            projects.sort(key=lambda p: p.last_active, reverse=True)

            return projects

        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            raise AppException(f"Error listing projects: {str(e)}")
