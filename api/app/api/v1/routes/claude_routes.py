"""
Claude Code API routes.
Defines the API endpoints and their OpenAPI documentation.
"""
from fastapi import APIRouter, Query
from typing import Optional

from app.api.v1.controllers.claude_controller import ClaudeController
from app.models.claude_models import (
    SessionsResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ProjectsResponse,
)

router = APIRouter(tags=["Claude"])

# Initialize controller
claude_controller = ClaudeController()


@router.get(
    "/sessions",
    response_model=SessionsResponse,
    summary="List Claude Code sessions",
    description="List available Claude Code sessions that can be resumed",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "sessions": [
                            {
                                "session_id": "3298a122-7fa3-41b6-a60a-304cd81a9d0a",
                                "project": "/Users/joecorrin/Development/app",
                                "preview": "First message preview text...",
                                "last_active": "2025-01-02T09:38:00Z",
                                "message_count": 12,
                            }
                        ]
                    }
                }
            },
        },
        400: {"description": "Bad request - invalid parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_sessions(
    limit: int = Query(
        20,
        description="Maximum number of sessions to return",
        ge=1,
        le=100,
    ),
    project: Optional[str] = Query(
        None,
        description="Filter by project path",
    ),
) -> SessionsResponse:
    """
    List available Claude Code sessions.

    Returns a list of sessions that can be resumed, with information about
    each session including the project, preview, and last active time.
    """
    return await claude_controller.list_sessions(limit=limit, project=project)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send message to Claude Code",
    description="Send a message to Claude Code, optionally resuming an existing session",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Claude's response text...",
                        "session_id": "3298a122-7fa3-41b6-a60a-304cd81a9d0a",
                        "exit_code": 0,
                        "stderr": "",
                    }
                }
            },
        },
        400: {"description": "Bad request - invalid message or parameters"},
        500: {"description": "Internal server error"},
    },
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to Claude Code.

    This endpoint executes a Claude Code CLI command with the provided message.
    You can optionally resume an existing session by providing a session_id.

    **Warning:** The `dangerously_skip_permissions` flag bypasses permission prompts.
    Only use this in trusted, automated environments.
    """
    return await claude_controller.chat(request)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Claude Code health check",
    description="Check if Claude Code CLI is available and configured",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "claude_version": "2.0.76",
                        "api_key_configured": True,
                    }
                }
            },
        },
        500: {"description": "Service unavailable"},
    },
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for Claude Code service.

    Verifies that:
    - Claude CLI is installed and accessible
    - Claude CLI version can be determined
    - ANTHROPIC_API_KEY environment variable is configured
    """
    return await claude_controller.health_check()


@router.get(
    "/projects",
    response_model=ProjectsResponse,
    summary="List Claude Code projects",
    description="List known projects (directories Claude Code has been used in)",
    responses={
        200: {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "example": {
                        "projects": [
                            {
                                "path": "/Users/joecorrin/Development/app",
                                "session_count": 235,
                                "last_active": "2025-01-02T09:38:00Z",
                            }
                        ]
                    }
                }
            },
        },
        500: {"description": "Internal server error"},
    },
)
async def list_projects() -> ProjectsResponse:
    """
    List all known Claude Code projects.

    Returns a list of projects (directories) where Claude Code has been used,
    along with the number of sessions and last active time for each project.
    """
    return await claude_controller.list_projects()
