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
from app.core.exceptions import AppException, BadRequestException

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
            AppException: If unable to list sessions
        """
        try:
            # Validate parameters
            if limit < 1 or limit > 100:
                raise BadRequestException("Limit must be between 1 and 100")

            sessions = self.session_service.list_sessions(limit=limit, project=project)

            logger.info(f"Listed {len(sessions)} sessions")
            return SessionsResponse(sessions=sessions)

        except BadRequestException:
            raise
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error in list_sessions controller: {str(e)}", exc_info=True)
            raise AppException(f"Unexpected error listing sessions: {str(e)}")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Handle POST request for chat endpoint.

        Args:
            request: ChatRequest with message and optional parameters

        Returns:
            ChatResponse with Claude's response

        Raises:
            BadRequestException: If request is invalid
            AppException: If chat execution fails
        """
        try:
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

        except BadRequestException:
            raise
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error in chat controller: {str(e)}", exc_info=True)
            raise AppException(f"Unexpected error in chat: {str(e)}")

    async def health_check(self) -> HealthResponse:
        """
        Handle GET request for health check endpoint.

        Returns:
            HealthResponse with Claude CLI status

        Raises:
            AppException: If health check fails
        """
        try:
            version = self.claude_service.get_version()
            api_key_configured = self.claude_service.check_api_key()

            logger.debug("Health check successful")

            return HealthResponse(
                status="ok",
                claude_version=version,
                api_key_configured=api_key_configured,
            )

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error in health_check controller: {str(e)}", exc_info=True)
            raise AppException(f"Unexpected error in health check: {str(e)}")

    async def list_projects(self) -> ProjectsResponse:
        """
        Handle GET request for projects endpoint.

        Returns:
            ProjectsResponse with list of projects

        Raises:
            AppException: If unable to list projects
        """
        try:
            projects = self.project_service.list_projects()

            logger.info(f"Listed {len(projects)} projects")
            return ProjectsResponse(projects=projects)

        except AppException:
            raise
        except Exception as e:
            logger.error(f"Error in list_projects controller: {str(e)}", exc_info=True)
            raise AppException(f"Unexpected error listing projects: {str(e)}")
