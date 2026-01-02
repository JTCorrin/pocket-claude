"""
Task storage and management service.
"""
import asyncio
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from app.models.task_models import TaskInfo, TaskStatus
from app.services.claude_service import ClaudeService
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class TaskStore:
    """
    In-memory task storage with automatic cleanup.

    Tasks are stored for a configured TTL (default 1 hour) after completion.
    Pending/running tasks are kept until they complete or fail.
    """

    def __init__(self, ttl_hours: int = 1):
        """
        Initialize task store.

        Args:
            ttl_hours: Time-to-live for completed tasks in hours
        """
        self._tasks: Dict[str, TaskInfo] = {}
        self._lock = asyncio.Lock()
        self.ttl_hours = ttl_hours

    async def create_task(
        self,
        message: str,
        session_id: Optional[str] = None,
        project_path: Optional[str] = None,
    ) -> TaskInfo:
        """
        Create a new task.

        Args:
            message: Message to send to Claude
            session_id: Optional session ID to resume
            project_path: Optional project path

        Returns:
            Created TaskInfo
        """
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        task = TaskInfo(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=message,
            session_id=session_id,
            project_path=project_path,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=self.ttl_hours),
        )

        async with self._lock:
            self._tasks[task_id] = task

        logger.info(f"Created task {task_id}")
        return task

    async def get_task(self, task_id: str) -> TaskInfo:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            TaskInfo

        Raises:
            NotFoundException: If task not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)

        if task is None:
            raise NotFoundException(f"Task not found: {task_id}")

        return task

    async def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
        stderr: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> TaskInfo:
        """
        Update task status and fields.

        Args:
            task_id: Task identifier
            status: New status
            result: Task result
            error: Error message
            exit_code: CLI exit code
            stderr: Standard error output
            session_id: Session ID (if extracted)

        Returns:
            Updated TaskInfo

        Raises:
            NotFoundException: If task not found
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise NotFoundException(f"Task not found: {task_id}")

            now = datetime.now(timezone.utc)

            if status is not None:
                task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if exit_code is not None:
                task.exit_code = exit_code
            if stderr is not None:
                task.stderr = stderr
            if session_id is not None:
                task.session_id = session_id

            task.updated_at = now

            # Update expiry when task completes/fails
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                task.expires_at = now + timedelta(hours=self.ttl_hours)

        logger.info(f"Updated task {task_id}: status={status}")
        return task

    async def cleanup_expired(self) -> int:
        """
        Remove expired tasks.

        Returns:
            Number of tasks removed
        """
        now = datetime.now(timezone.utc)
        removed = 0

        async with self._lock:
            expired_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status
                in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                and task.expires_at < now
            ]

            for task_id in expired_ids:
                del self._tasks[task_id]
                removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired tasks")

        return removed

    async def get_all_tasks(self) -> list[TaskInfo]:
        """Get all tasks (for debugging/admin)."""
        async with self._lock:
            return list(self._tasks.values())


# Global task store instance
_task_store: Optional[TaskStore] = None


def get_task_store() -> TaskStore:
    """Get or create the global task store."""
    global _task_store
    if _task_store is None:
        _task_store = TaskStore()
    return _task_store


class TaskExecutor:
    """
    Executes Claude Code tasks in background threads.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize task executor.

        Args:
            max_workers: Maximum number of concurrent tasks
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._claude_service = ClaudeService()
        self._task_store = get_task_store()

    async def execute_task(self, task_id: str, dangerously_skip_permissions: bool = False) -> None:
        """
        Execute a Claude Code task in the background.

        Args:
            task_id: Task identifier
            dangerously_skip_permissions: Skip permission prompts
        """
        # Get task details
        task = await self._task_store.get_task(task_id)

        # Update status to running
        await self._task_store.update_task(task_id, status=TaskStatus.RUNNING)

        try:
            # Execute in thread pool (blocking call)
            loop = asyncio.get_event_loop()
            response, session_id, exit_code, stderr = await loop.run_in_executor(
                self._executor,
                self._claude_service.execute_chat,
                task.message,
                task.session_id,
                task.project_path,
                dangerously_skip_permissions,
            )

            # Update task with result
            await self._task_store.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                result=response,
                session_id=session_id,
                exit_code=exit_code,
                stderr=stderr,
            )

            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}", exc_info=True)

            # Update task with error
            await self._task_store.update_task(
                task_id,
                status=TaskStatus.FAILED,
                error=str(e),
            )

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)


# Global task executor instance
_task_executor: Optional[TaskExecutor] = None


def get_task_executor() -> TaskExecutor:
    """Get or create the global task executor."""
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
    return _task_executor


async def cleanup_expired_tasks_periodically():
    """Background task to cleanup expired tasks."""
    task_store = get_task_store()

    while True:
        try:
            await asyncio.sleep(300)  # Run every 5 minutes
            await task_store.cleanup_expired()
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}", exc_info=True)
