"""
Models for async task management.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    """Information about an async task."""

    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    message: str = Field(..., description="Original message sent to Claude")
    session_id: Optional[str] = Field(None, description="Session ID if resuming")
    project_path: Optional[str] = Field(None, description="Project path if specified")
    result: Optional[str] = Field(None, description="Claude's response (when completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    exit_code: Optional[int] = Field(None, description="CLI exit code (when completed)")
    stderr: Optional[str] = Field(None, description="Standard error output")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: datetime = Field(..., description="Task expiration timestamp")


class TaskResponse(BaseModel):
    """Response for task creation."""

    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    message: str = Field(
        ..., description="Status message (e.g., 'Task created and queued')"
    )
