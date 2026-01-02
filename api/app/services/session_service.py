"""
Service for managing Claude Code sessions.
"""
import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from app.models.claude_models import SessionInfo
from app.core.exceptions import (
    NotFoundException,
    AppException,
    FileSystemException,
)
from app.utils.path_utils import decode_project_path

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing Claude Code sessions."""

    def __init__(self):
        """Initialize the session service."""
        self.claude_dir = Path.home() / ".claude"
        self.projects_dir = self.claude_dir / "projects"

    def _parse_session_file(self, session_file: Path) -> Optional[SessionInfo]:
        """
        Parse a session JSONL file to extract session information.

        Args:
            session_file: Path to the session file

        Returns:
            SessionInfo object or None if parsing fails
        """
        try:
            session_id = session_file.stem
            project_folder = session_file.parent.name
            project_path = decode_project_path(project_folder)

            # Read the JSONL file
            user_messages = []
            last_timestamp = None

            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())

                        # Track timestamps
                        if "timestamp" in entry:
                            timestamp_str = entry["timestamp"]
                            try:
                                timestamp = datetime.fromisoformat(
                                    timestamp_str.replace("Z", "+00:00")
                                )
                                if last_timestamp is None or timestamp > last_timestamp:
                                    last_timestamp = timestamp
                            except (ValueError, AttributeError):
                                # Ignore malformed or missing timestamps; we'll fall back
                                # to the file's modification time if no valid timestamp is found.
                                pass

                        # Collect user messages
                        if entry.get("type") == "user":
                            message_content = entry.get("message", {}).get(
                                "content", ""
                            )
                            if message_content:
                                user_messages.append(message_content)

                    except json.JSONDecodeError:
                        continue

            # Use file modification time if no timestamp found
            if last_timestamp is None:
                last_timestamp = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)

            # Get preview from first user message
            preview = user_messages[0] if user_messages else "No messages"
            # Truncate preview to reasonable length
            if len(preview) > 100:
                preview = preview[:97] + "..."

            return SessionInfo(
                session_id=session_id,
                project=project_path,
                preview=preview,
                last_active=last_timestamp,
                message_count=len(user_messages),
            )

        except Exception as e:
            logger.warning(f"Error parsing session file {session_file}: {str(e)}")
            return None

    def list_sessions(
        self, limit: int = 20, project: Optional[str] = None
    ) -> list[SessionInfo]:
        """
        List available Claude Code sessions.

        Args:
            limit: Maximum number of sessions to return
            project: Optional project path to filter by

        Returns:
            List of SessionInfo objects

        Raises:
            AppException: If unable to read sessions
        """
        try:
            if not self.projects_dir.exists():
                logger.warning(f"Projects directory does not exist: {self.projects_dir}")
                return []

            sessions = []

            # Iterate through project directories
            for project_dir in self.projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                # Decode project path
                project_path = decode_project_path(project_dir.name)

                # Filter by project if specified
                if project and project_path != project:
                    continue

                # Find all .jsonl files in the project directory
                for session_file in project_dir.glob("*.jsonl"):
                    session_info = self._parse_session_file(session_file)
                    if session_info:
                        sessions.append(session_info)

            # Sort by last_active descending
            sessions.sort(key=lambda s: s.last_active, reverse=True)

            # Apply limit
            return sessions[:limit]

        except Exception as e:
            logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
            raise FileSystemException(f"Error listing sessions: {str(e)}")

    def get_session(self, session_id: str) -> SessionInfo:
        """
        Get a specific session by ID.

        Args:
            session_id: The session ID to retrieve

        Returns:
            SessionInfo object

        Raises:
            NotFoundException: If session not found
            AppException: If unable to read session
        """
        try:
            if not self.projects_dir.exists():
                raise NotFoundException(f"Session not found: {session_id}")

            # Search through all project directories
            for project_dir in self.projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                session_file = project_dir / f"{session_id}.jsonl"
                if session_file.exists():
                    session_info = self._parse_session_file(session_file)
                    if session_info:
                        return session_info

            raise NotFoundException(f"Session not found: {session_id}")

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {str(e)}", exc_info=True)
            raise FileSystemException(f"Error getting session: {str(e)}")
