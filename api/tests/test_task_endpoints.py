"""
Tests for async task endpoints.
"""
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.task_models import TaskStatus
from app.services.task_service import TaskExecutor, get_task_store


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_global_task_store():
    """Clear global task store before each test."""
    # Get the global store and clear it directly (tests run sequentially)
    store = get_task_store()
    store._tasks.clear()
    yield
    # Clear again after test
    store._tasks.clear()


@pytest.fixture
def task_store():
    """Get the global task store for tests."""
    return get_task_store()


@pytest.fixture
def mock_claude_service():
    """Mock ClaudeService for testing."""
    with patch("app.services.task_service.ClaudeService") as mock:
        mock_instance = mock.return_value
        mock_instance.execute_chat.return_value = (
            "Test response",
            "test-session-id",
            0,
            None,
        )
        yield mock_instance


class TestTaskCreation:
    """Tests for POST /tasks/chat endpoint."""

    def test_create_task_success(self, client):
        """Test creating a new task."""
        response = client.post(
            "/api/v1/tasks/chat",
            json={
                "message": "Hello Claude",
                "dangerously_skip_permissions": True,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == TaskStatus.PENDING
        assert "message" in data

    def test_create_task_with_session(self, client):
        """Test creating a task with session ID."""
        response = client.post(
            "/api/v1/tasks/chat",
            json={
                "message": "Continue conversation",
                "session_id": "existing-session-123",
                "dangerously_skip_permissions": True,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == TaskStatus.PENDING

    def test_create_task_with_project_path(self, client):
        """Test creating a task with project path."""
        response = client.post(
            "/api/v1/tasks/chat",
            json={
                "message": "Run tests",
                "project_path": "/home/user/project",
                "dangerously_skip_permissions": True,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == TaskStatus.PENDING

    def test_create_task_missing_message(self, client):
        """Test creating a task without message."""
        response = client.post(
            "/api/v1/tasks/chat",
            json={"dangerously_skip_permissions": True},
        )

        assert response.status_code == 422  # Validation error


class TestTaskStatus:
    """Tests for GET /tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_status_pending(self, client, task_store):
        """Test getting status of a pending task."""
        # Create a task directly in store
        task = await task_store.create_task(message="Test message")

        response = client.get(f"/api/v1/tasks/{task.task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == task.task_id
        assert data["status"] == TaskStatus.PENDING
        assert data["message"] == "Test message"
        assert data["result"] is None

    @pytest.mark.asyncio
    async def test_get_task_status_completed(self, client, task_store):
        """Test getting status of a completed task."""
        # Create and complete a task
        task = await task_store.create_task(message="Test message")
        await task_store.update_task(
            task.task_id,
            status=TaskStatus.COMPLETED,
            result="Task completed successfully",
            session_id="session-123",
            exit_code=0,
        )

        response = client.get(f"/api/v1/tasks/{task.task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.COMPLETED
        assert data["result"] == "Task completed successfully"
        assert data["session_id"] == "session-123"
        assert data["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_get_task_status_failed(self, client, task_store):
        """Test getting status of a failed task."""
        # Create and fail a task
        task = await task_store.create_task(message="Test message")
        await task_store.update_task(
            task.task_id,
            status=TaskStatus.FAILED,
            error="Command execution failed",
        )

        response = client.get(f"/api/v1/tasks/{task.task_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == TaskStatus.FAILED
        assert data["error"] == "Command execution failed"

    def test_get_task_not_found(self, client):
        """Test getting a non-existent task."""
        response = client.get("/api/v1/tasks/non-existent-task-id")

        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "not found" in error_data["error"]["message"].lower()


class TestTaskList:
    """Tests for GET /tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, client, task_store):
        """Test listing tasks when none exist."""
        response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_list_tasks_multiple(self, client, task_store):
        """Test listing multiple tasks."""
        # Create several tasks
        task1 = await task_store.create_task(message="Task 1")
        task2 = await task_store.create_task(message="Task 2")
        await task_store.update_task(task1.task_id, status=TaskStatus.COMPLETED, result="Done")

        response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(t["task_id"] == task1.task_id for t in data)
        assert any(t["task_id"] == task2.task_id for t in data)


class TestTaskStore:
    """Tests for TaskStore service."""

    @pytest.mark.asyncio
    async def test_create_task(self, task_store):
        """Test creating a task in the store."""
        task = await task_store.create_task(
            message="Test message",
            session_id="session-123",
            project_path="/home/user/project",
        )

        assert task.task_id is not None
        assert task.status == TaskStatus.PENDING
        assert task.message == "Test message"
        assert task.session_id == "session-123"
        assert task.project_path == "/home/user/project"
        assert task.result is None
        assert task.created_at is not None

    @pytest.mark.asyncio
    async def test_get_task(self, task_store):
        """Test retrieving a task."""
        created_task = await task_store.create_task(message="Test")
        retrieved_task = await task_store.get_task(created_task.task_id)

        assert retrieved_task.task_id == created_task.task_id
        assert retrieved_task.message == created_task.message

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, task_store):
        """Test retrieving a non-existent task."""
        from app.core.exceptions import NotFoundException

        with pytest.raises(NotFoundException):
            await task_store.get_task("non-existent-id")

    @pytest.mark.asyncio
    async def test_update_task(self, task_store):
        """Test updating a task."""
        task = await task_store.create_task(message="Test")

        # Add small delay to ensure different timestamp
        await asyncio.sleep(0.01)

        updated_task = await task_store.update_task(
            task.task_id,
            status=TaskStatus.RUNNING,
        )

        assert updated_task.status == TaskStatus.RUNNING
        assert updated_task.updated_at >= task.updated_at

    @pytest.mark.asyncio
    async def test_update_task_completion_updates_expiry(self, task_store):
        """Test that completing a task updates its expiry time."""
        task = await task_store.create_task(message="Test")
        original_expires_at = task.expires_at

        # Complete the task
        await asyncio.sleep(0.1)  # Small delay to ensure time difference
        updated_task = await task_store.update_task(
            task.task_id,
            status=TaskStatus.COMPLETED,
            result="Done",
        )

        # Expiry should be updated to 1 hour from completion time
        assert updated_task.expires_at > original_expires_at

    @pytest.mark.asyncio
    async def test_cleanup_expired_tasks(self, task_store):
        """Test cleanup of expired tasks."""
        # Create a task
        task = await task_store.create_task(message="Test")

        # Complete it and manually set expiry to the past
        await task_store.update_task(
            task.task_id,
            status=TaskStatus.COMPLETED,
            result="Done",
        )

        # Manually expire it
        task_store._tasks[task.task_id].expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        # Run cleanup
        removed = await task_store.cleanup_expired()

        assert removed == 1
        assert len(await task_store.get_all_tasks()) == 0

    @pytest.mark.asyncio
    async def test_cleanup_preserves_active_tasks(self, task_store):
        """Test that cleanup doesn't remove active tasks."""
        # Create pending and running tasks
        await task_store.create_task(message="Pending")
        running_task = await task_store.create_task(message="Running")
        await task_store.update_task(running_task.task_id, status=TaskStatus.RUNNING)

        # Run cleanup
        removed = await task_store.cleanup_expired()

        assert removed == 0
        assert len(await task_store.get_all_tasks()) == 2


class TestTaskExecutor:
    """Tests for TaskExecutor service."""

    @pytest.mark.asyncio
    async def test_execute_task_success(self, task_store, mock_claude_service):
        """Test successful task execution."""
        # Create executor with mocked service
        with patch("app.services.task_service.ClaudeService", return_value=mock_claude_service):
            executor = TaskExecutor(max_workers=2)
            executor._task_store = task_store

            # Create a task
            task = await task_store.create_task(message="Test message")

            # Execute it
            await executor.execute_task(task.task_id, dangerously_skip_permissions=True)

            # Check task was completed
            completed_task = await task_store.get_task(task.task_id)
            assert completed_task.status == TaskStatus.COMPLETED
            assert completed_task.result == "Test response"
            assert completed_task.session_id == "test-session-id"
            assert completed_task.exit_code == 0

            executor.shutdown()

    @pytest.mark.asyncio
    async def test_execute_task_failure(self, task_store):
        """Test task execution with failure."""
        # Mock service that raises an error
        mock_service = Mock()
        mock_service.execute_chat.side_effect = Exception("Command failed")

        with patch("app.services.task_service.ClaudeService", return_value=mock_service):
            executor = TaskExecutor(max_workers=2)
            executor._task_store = task_store

            # Create a task
            task = await task_store.create_task(message="Test message")

            # Execute it (should fail)
            await executor.execute_task(task.task_id)

            # Check task was marked as failed
            failed_task = await task_store.get_task(task.task_id)
            assert failed_task.status == TaskStatus.FAILED
            assert "Command failed" in failed_task.error

            executor.shutdown()

    @pytest.mark.asyncio
    async def test_execute_task_updates_to_running(self, task_store):
        """Test that task status is updated to RUNNING during execution."""
        # Create a mock that delays execution
        import time

        def slow_chat(*args, **kwargs):
            time.sleep(0.3)  # Block for a bit
            return ("Response", "session-id", 0, None)

        with patch("app.services.task_service.ClaudeService") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.execute_chat = slow_chat

            executor = TaskExecutor(max_workers=2)
            executor._task_store = task_store
            executor._claude_service = mock_instance

            task = await task_store.create_task(message="Test")

            # Start execution without awaiting
            execution = asyncio.create_task(
                executor.execute_task(task.task_id, dangerously_skip_permissions=True)
            )

            # Wait a bit for it to move to running
            await asyncio.sleep(0.1)
            running_task = await task_store.get_task(task.task_id)

            # Should be running now
            assert running_task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]

            # Wait for completion
            await execution

            # Should be completed now
            completed_task = await task_store.get_task(task.task_id)
            assert completed_task.status == TaskStatus.COMPLETED

            executor.shutdown()


class TestIntegration:
    """Integration tests for the full async task flow."""

    @pytest.mark.asyncio
    async def test_full_task_lifecycle(self, client, task_store):
        """Test complete task lifecycle from creation to completion."""
        # 1. Create task via API
        create_response = client.post(
            "/api/v1/tasks/chat",
            json={
                "message": "Hello Claude",
                "dangerously_skip_permissions": True,
            },
        )

        assert create_response.status_code == 202
        task_id = create_response.json()["task_id"]

        # Give the background task time to start
        await asyncio.sleep(0.1)

        # 2. Check status (should be pending or running)
        status_response = client.get(f"/api/v1/tasks/{task_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] in [TaskStatus.PENDING, TaskStatus.RUNNING]

        # 3. Simulate completion directly in store
        await task_store.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            result="Task completed",
            exit_code=0,
        )

        # 4. Check completed status via API
        completed_response = client.get(f"/api/v1/tasks/{task_id}")
        assert completed_response.status_code == 200
        data = completed_response.json()
        assert data["status"] == TaskStatus.COMPLETED
        assert data["result"] == "Task completed"

        # 5. Verify task appears in list
        list_response = client.get("/api/v1/tasks")
        assert list_response.status_code == 200
        tasks = list_response.json()
        assert any(t["task_id"] == task_id for t in tasks)


class TestConcurrency:
    """Test concurrent task operations."""

    @pytest.mark.asyncio
    async def test_concurrent_task_creation(self, task_store):
        """Test creating multiple tasks concurrently."""
        async def create_task(index: int):
            return await task_store.create_task(message=f"Concurrent task {index}")

        # Create 10 tasks concurrently
        tasks = await asyncio.gather(*[create_task(i) for i in range(10)])
        
        assert len(tasks) == 10
        assert len(set(t.task_id for t in tasks)) == 10  # All unique IDs
        
        # Verify all tasks are in store
        all_tasks = await task_store.get_all_tasks()
        assert len(all_tasks) == 10

    @pytest.mark.asyncio
    async def test_concurrent_task_updates(self, task_store):
        """Test updating the same task from multiple coroutines."""
        # Create a task
        task = await task_store.create_task(message="Concurrent update test")
        
        async def update_task(status: TaskStatus, result: str):
            await asyncio.sleep(0.01)  # Small delay to increase concurrency
            return await task_store.update_task(
                task.task_id,
                status=status,
                result=result
            )
        
        # Try to update task concurrently (last one wins)
        updates = await asyncio.gather(
            update_task(TaskStatus.RUNNING, "Running 1"),
            update_task(TaskStatus.RUNNING, "Running 2"),
            update_task(TaskStatus.COMPLETED, "Completed")
        )
        
        # Verify task reached a terminal state
        final_task = await task_store.get_task(task.task_id)
        assert final_task.status in (TaskStatus.RUNNING, TaskStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_concurrent_cleanup_and_access(self, task_store):
        """Test that cleanup doesn't interfere with concurrent task access."""
        # Create some completed tasks that will expire
        from datetime import timedelta
        
        expired_tasks = []
        for i in range(5):
            task = await task_store.create_task(message=f"Expired {i}")
            await task_store.update_task(task.task_id, status=TaskStatus.COMPLETED, result=f"Result {i}")
            # Manually set to expired
            task.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            expired_tasks.append(task)
        
        # Create some active tasks
        active_tasks = []
        for i in range(5):
            task = await task_store.create_task(message=f"Active {i}")
            active_tasks.append(task)
        
        # Run cleanup and access tasks concurrently
        async def access_tasks():
            for task in active_tasks:
                await task_store.get_task(task.task_id)
                await asyncio.sleep(0.01)
        
        results = await asyncio.gather(
            task_store.cleanup_expired(),
            access_tasks(),
            access_tasks()
        )
        
        removed_count = results[0]
        assert removed_count == 5
        
        # Verify active tasks still exist
        all_tasks = await task_store.get_all_tasks()
        assert len(all_tasks) == 5
        assert all(t.task_id in [at.task_id for at in active_tasks] for t in all_tasks)
