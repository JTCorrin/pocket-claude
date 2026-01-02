"""
Task management routes.
Defines the API endpoints for async task operations.
"""
from fastapi import APIRouter
from typing import List

from app.api.v1.controllers.task_controller import TaskController
from app.models.task_models import TaskInfo, TaskResponse
from app.models.claude_models import ChatRequest

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Initialize controller
task_controller = TaskController()


@router.post(
    "/chat",
    response_model=TaskResponse,
    summary="Create async chat task",
    description="Submit a chat message and get a task ID immediately. Poll the task status to get results.",
    responses={
        202: {
            "description": "Task created and accepted for processing",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "pending",
                        "message": "Task created and queued for execution",
                    }
                }
            },
        },
        400: {"description": "Bad request - invalid message or parameters"},
        500: {"description": "Internal server error"},
    },
    status_code=202,
)
async def create_chat_task(request: ChatRequest) -> TaskResponse:
    """
    Create an async chat task.

    This endpoint accepts a chat request and returns immediately with a task ID.
    The Claude Code CLI execution happens in the background.

    Use this endpoint when:
    - The app might be backgrounded during execution
    - You want to show progress/loading states
    - The task might take a long time

    To get results:
    1. Poll GET /tasks/{task_id} until status is 'completed' or 'failed'
    2. Retrieve the result from the completed task

    **Note:** Tasks expire 1 hour after completion.
    """
    return await task_controller.create_chat_task(request)


@router.get(
    "/{task_id}",
    response_model=TaskInfo,
    summary="Get task status and result",
    description="Check the status of an async task and retrieve results when completed",
    responses={
        200: {
            "description": "Task information retrieved",
            "content": {
                "application/json": {
                    "examples": {
                        "pending": {
                            "summary": "Task pending",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "pending",
                                "message": "Explain this codebase",
                                "session_id": None,
                                "project_path": None,
                                "result": None,
                                "error": None,
                                "created_at": "2025-01-02T10:00:00Z",
                                "updated_at": "2025-01-02T10:00:00Z",
                                "expires_at": "2025-01-02T11:00:00Z",
                            },
                        },
                        "running": {
                            "summary": "Task running",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "running",
                                "message": "Explain this codebase",
                                "session_id": None,
                                "project_path": "/path/to/project",
                                "result": None,
                                "error": None,
                                "created_at": "2025-01-02T10:00:00Z",
                                "updated_at": "2025-01-02T10:00:05Z",
                                "expires_at": "2025-01-02T11:00:00Z",
                            },
                        },
                        "completed": {
                            "summary": "Task completed",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "completed",
                                "message": "Explain this codebase",
                                "session_id": "abc-123-def",
                                "project_path": "/path/to/project",
                                "result": "This codebase is a FastAPI application...",
                                "error": None,
                                "exit_code": 0,
                                "stderr": "",
                                "created_at": "2025-01-02T10:00:00Z",
                                "updated_at": "2025-01-02T10:02:30Z",
                                "expires_at": "2025-01-02T11:02:30Z",
                            },
                        },
                        "failed": {
                            "summary": "Task failed",
                            "value": {
                                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                "status": "failed",
                                "message": "Explain this codebase",
                                "session_id": None,
                                "project_path": None,
                                "result": None,
                                "error": "Claude CLI not found",
                                "created_at": "2025-01-02T10:00:00Z",
                                "updated_at": "2025-01-02T10:00:01Z",
                                "expires_at": "2025-01-02T11:00:01Z",
                            },
                        },
                    }
                }
            },
        },
        404: {"description": "Task not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_task_status(task_id: str) -> TaskInfo:
    """
    Get task status and result.

    Poll this endpoint to check if your task has completed.
    When status is 'completed', the result field will contain Claude's response.

    **Polling recommendations:**
    - Start with 1-2 second intervals
    - Use exponential backoff (2s, 4s, 8s, up to 30s)
    - Stop polling after task completes or fails
    - Tasks expire 1 hour after completion

    **Status values:**
    - `pending`: Task queued, not yet started
    - `running`: Task is executing
    - `completed`: Task finished successfully, check `result` field
    - `failed`: Task failed, check `error` field
    """
    return await task_controller.get_task_status(task_id)


@router.get(
    "",
    response_model=List[TaskInfo],
    summary="List all tasks (admin/debug)",
    description="Get all tasks in the system",
    responses={
        200: {
            "description": "List of all tasks",
        },
    },
)
async def list_tasks() -> List[TaskInfo]:
    """
    List all tasks (for debugging/admin purposes).

    Returns all tasks currently in the system, including pending, running, and completed tasks.
    """
    return await task_controller.list_tasks()
