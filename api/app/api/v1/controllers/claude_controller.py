"""
Controller for Claude Code endpoints.
Handles HTTP requests and coordinates with service layer.
"""
import logging
from typing import Optional
from app.models.claude_models import (
    SessionsResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ProjectsResponse,
)
from app.services.claude_service import ClaudeService
from app.services.session_service import SessionService
from app.services.project_service import ProjectService
from app.core.exceptions import BadRequestException

logger = logging.getLogger(__name__)


class ClaudeController:
    """Controller for Claude Code endpoints."""

    def __init__(self):
        """Initialize controller with service dependencies."""
        self.claude_service = ClaudeService()
        self.session_service = SessionService()
        self.project_service = ProjectService()

    async def list_sessions(
        self, limit: int = 20, project: Optional[str] = None
    ) -> SessionsResponse:
        """
        Handle GET request for sessions endpoint.

        Args:
            limit: Maximum number of sessions to return
            project: Optional project path filter

        Returns:
            SessionsResponse with list of sessions

        Raises:
            BadRequestException: If parameters are invalid
            FileSystemException: If unable to read session files
        """
        # Validate parameters
        if limit < 1 or limit > 100:
            raise BadRequestException("Limit must be between 1 and 100")

        sessions = self.session_service.list_sessions(limit=limit, project=project)

        logger.info(f"Listed {len(sessions)} sessions")
        return SessionsResponse(sessions=sessions)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle POST request for chat endpoint.

        Args:
            request: ChatRequest with message and optional parameters

        Returns:
            ChatResponse with Claude's response

        Raises:
            BadRequestException: If request is invalid
            CLINotFoundException: If Claude CLI is not found
            CommandTimeoutException: If command execution times out
        """
        # Execute chat command
        response, session_id, exit_code, stderr = (
            self.claude_service.execute_chat(
                message=request.message,
                session_id=request.session_id,
                project_path=request.project_path,
                dangerously_skip_permissions=request.dangerously_skip_permissions,
            )
        )

        logger.info(
            f"Chat executed successfully. Session: {session_id}, Exit code: {exit_code}"
        )

        return ChatResponse(
            response=response,
            session_id=session_id,
            exit_code=exit_code,
            stderr=stderr,
        )

    async def health_check(self) -> HealthResponse:
        """
        Handle GET request for health check endpoint.

        Returns:
            HealthResponse with Claude CLI status

        Raises:
            CLINotFoundException: If Claude CLI is not found
            CommandTimeoutException: If health check times out
        """
        version = self.claude_service.get_version()
        api_key_configured = self.claude_service.check_api_key()

        logger.debug("Health check successful")

        return HealthResponse(
            status="ok",
            claude_version=version,
            api_key_configured=api_key_configured,
        )

    async def list_projects(self) -> ProjectsResponse:
        """
        Handle GET request for projects endpoint.

        Returns:
            ProjectsResponse with list of projects

        Raises:
            FileSystemException: If unable to read project directories
        """
        projects = self.project_service.list_projects()

        logger.info(f"Listed {len(projects)} projects")
        return ProjectsResponse(projects=projects)
