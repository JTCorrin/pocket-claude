"""
Controller for async task management.
Handles HTTP requests for task status and results.
"""
import logging
import asyncio
from typing import Optional

from app.models.task_models import TaskInfo, TaskResponse
from app.models.claude_models import ChatRequest
from app.services.task_service import get_task_store, get_task_executor
from app.core.exceptions import NotFoundException, BadRequestException

logger = logging.getLogger(__name__)


class TaskController:
    """Controller for async task endpoints."""

    def __init__(self):
        """Initialize controller with service dependencies."""
        self.task_store = get_task_store()
        self.task_executor = get_task_executor()

    async def create_chat_task(self, request: ChatRequest) -> TaskResponse:
        """
        Create an async chat task and return immediately.

        Args:
            request: ChatRequest with message and optional parameters

        Returns:
            TaskResponse with task ID and status

        Raises:
            BadRequestException: If request is invalid
        """
        try:
            # Create task in store
            task = await self.task_store.create_task(
                message=request.message,
                session_id=request.session_id,
                project_path=request.project_path,
            )

            # Execute task in background (fire and forget)
            asyncio.create_task(
                self.task_executor.execute_task(
                    task.task_id, request.dangerously_skip_permissions
                )
            )

            logger.info(f"Created async chat task {task.task_id}")

            return TaskResponse(
                task_id=task.task_id,
                status=task.status,
                message="Task created and queued for execution",
            )

        except BadRequestException:
            raise
        except Exception as e:
            logger.error(f"Error creating chat task: {str(e)}", exc_info=True)
            raise BadRequestException(f"Failed to create task: {str(e)}")

    async def get_task_status(self, task_id: str) -> TaskInfo:
        """
        Get task status and result.

        Args:
            task_id: Task identifier

        Returns:
            TaskInfo with current status and result (if completed)

        Raises:
            NotFoundException: If task not found
        """
        try:
            task = await self.task_store.get_task(task_id)
            logger.debug(f"Retrieved task {task_id}: status={task.status}")
            return task

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving task {task_id}: {str(e)}", exc_info=True)
            raise NotFoundException(f"Task not found: {task_id}")

    async def list_tasks(self) -> list[TaskInfo]:
        """
        List all tasks (for debugging/admin).

        Returns:
            List of all TaskInfo objects
        """
        tasks = await self.task_store.get_all_tasks()
        logger.info(f"Listed {len(tasks)} tasks")
        return tasks
