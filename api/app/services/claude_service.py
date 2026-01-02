"""
Service for interacting with Claude Code CLI.
"""
import subprocess
import logging
import os
import re
from typing import Optional, Tuple
from app.core.exceptions import BadRequestException, AppException

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for executing Claude Code CLI commands."""

    def __init__(self):
        """Initialize the Claude service."""
        self.timeout = 300  # 5 minutes default timeout

    def get_version(self) -> str:
        """
        Get the Claude CLI version.

        Returns:
            Version string

        Raises:
            AppException: If unable to get version
        """
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Extract version from output (e.g., "claude 2.0.76")
                version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
                if version_match:
                    return version_match.group(1)
                return result.stdout.strip()
            else:
                logger.error(f"Failed to get Claude version: {result.stderr}")
                raise AppException("Unable to determine Claude version")

        except FileNotFoundError:
            raise AppException("Claude CLI not found. Please ensure it is installed.")
        except subprocess.TimeoutExpired:
            raise AppException("Claude version check timed out")
        except Exception as e:
            logger.error(f"Error getting Claude version: {str(e)}")
            raise AppException(f"Error checking Claude version: {str(e)}")

    def check_api_key(self) -> bool:
        """
        Check if ANTHROPIC_API_KEY is configured.

        Returns:
            True if API key is set, False otherwise
        """
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def execute_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        project_path: Optional[str] = None,
        dangerously_skip_permissions: bool = False,
    ) -> Tuple[str, str, int, str]:
        """
        Execute a chat command with Claude Code CLI.

        Args:
            message: The message to send
            session_id: Optional session ID to resume
            project_path: Optional project path to run in
            dangerously_skip_permissions: Skip permission prompts

        Returns:
            Tuple of (response, session_id, exit_code, stderr)

        Raises:
            BadRequestException: If inputs are invalid
            AppException: If execution fails
        """
        # Validate inputs
        if not message or not message.strip():
            raise BadRequestException("Message cannot be empty")

        if project_path:
            # Basic path validation to prevent path traversal
            project_path = os.path.abspath(project_path)
            if not os.path.exists(project_path):
                raise BadRequestException(f"Project path does not exist: {project_path}")
            if not os.path.isdir(project_path):
                raise BadRequestException(f"Project path is not a directory: {project_path}")

        # Build command
        cmd = ["claude", "-p", message]

        if session_id:
            cmd.extend(["--resume", session_id])

        if dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        logger.info(f"Executing Claude command: {' '.join(cmd[:3])}...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=project_path,
            )

            # Extract session ID from output if not resuming
            extracted_session_id = session_id
            if not extracted_session_id:
                # Try to extract session ID from stderr or stdout
                # Claude CLI typically outputs session info
                session_match = re.search(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                    result.stdout + result.stderr,
                )
                if session_match:
                    extracted_session_id = session_match.group(0)
                else:
                    # If we can't extract session ID, generate a placeholder
                    logger.warning("Could not extract session ID from Claude output")
                    extracted_session_id = "unknown"

            return (
                result.stdout,
                extracted_session_id,
                result.returncode,
                result.stderr,
            )

        except subprocess.TimeoutExpired:
            logger.error(f"Claude command timed out after {self.timeout} seconds")
            raise AppException(
                f"Claude command timed out after {self.timeout} seconds"
            )
        except FileNotFoundError:
            raise AppException("Claude CLI not found. Please ensure it is installed.")
        except Exception as e:
            logger.error(f"Error executing Claude command: {str(e)}")
            raise AppException(f"Error executing Claude command: {str(e)}")
