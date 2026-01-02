"""
Pydantic models for Claude Code API endpoints.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# Session Models
class SessionInfo(BaseModel):
    """Information about a Claude Code session."""

    session_id: str = Field(..., description="Unique session identifier")
    project: str = Field(..., description="Project path")
    preview: str = Field(..., description="First message preview")
    last_active: datetime = Field(..., description="Last active timestamp")
    message_count: int = Field(..., description="Number of messages in session")


class SessionsResponse(BaseModel):
    """Response for GET /sessions endpoint."""

    sessions: list[SessionInfo] = Field(..., description="List of sessions")


# Chat Models
class ChatRequest(BaseModel):
    """Request body for POST /chat endpoint."""

    message: str = Field(..., description="Message to send to Claude Code")
    session_id: Optional[str] = Field(
        None, description="Optional session ID to resume"
    )
    project_path: Optional[str] = Field(None, description="Optional project path")
    dangerously_skip_permissions: bool = Field(
        False, description="Skip permission prompts (use with caution)"
    )


class ChatResponse(BaseModel):
    """Response for POST /chat endpoint."""

    response: str = Field(..., description="Claude's response text")
    session_id: str = Field(..., description="Session ID")
    exit_code: int = Field(..., description="CLI exit code")
    stderr: str = Field("", description="Standard error output")


# Health Models
class HealthResponse(BaseModel):
    """Response for GET /health endpoint."""

    status: str = Field(..., description="Health status")
    claude_version: str = Field(..., description="Claude CLI version")
    api_key_configured: bool = Field(
        ..., description="Whether API key is configured"
    )


# Project Models
class ProjectInfo(BaseModel):
    """Information about a Claude Code project."""

    path: str = Field(..., description="Project path")
    session_count: int = Field(..., description="Number of sessions")
    last_active: datetime = Field(..., description="Last active timestamp")


class ProjectsResponse(BaseModel):
    """Response for GET /projects endpoint."""

    projects: list[ProjectInfo] = Field(..., description="List of projects")
