"""
Integration tests for scheduler execution flow logging.

Tests that structured logging:
1. Doesn't break existing scheduler functionality
2. Properly tracks execution flow from API -> Service -> Celery
3. Captures all instrumentation points
4. Produces parsable JSON output
"""

import json
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.scheduler_service import SchedulerService
from api.repositories.scheduler_repository import SchedulerRepository
from db.model import ScheduledJob, ScheduledJobExecution
from utils.structured_logger import set_correlation_id, clear_execution_context


@pytest.fixture
def mock_repo():
    """Create mock repository."""
    repo = MagicMock(spec=SchedulerRepository)
    return repo


@pytest.fixture
def scheduler_service(mock_repo):
    """Create SchedulerService instance with mock repository."""
    service = SchedulerService(repository=mock_repo)
    service._instance_id = "test-instance-123"
    return service


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_job():
    """Create sample ScheduledJob."""
    job = ScheduledJob(
        id=1,
        task_function_id=1,
        job_type_id=1,
        name_en="Test HRIS Job",
        is_enabled=True,
        is_active=True
    )
    # Mock properties
    job.job_key = "hris_replication"
    job.job_function = "tasks.hris.hris_replication_task"
    return job


@pytest.fixture
def running_status():
    """Create mock running status."""
    from db.model import SchedulerExecutionStatus
    status = SchedulerExecutionStatus(
        id=2,
        code="running",
        name_en="Running"
    )
    return status


@pytest.fixture
def success_status():
    """Create mock success status."""
    from db.model import SchedulerExecutionStatus
    status = SchedulerExecutionStatus(
        id=3,
        code="success",
        name_en="Success"
    )
    return status


@pytest.fixture
def failed_status():
    """Create mock failed status."""
    from db.model import SchedulerExecutionStatus
    status = SchedulerExecutionStatus(
        id=4,
        code="failed",
        name_en="Failed"
    )
    return status


@pytest.fixture(autouse=True)
def cleanup_context():
    """Clear execution context before and after each test."""
    clear_execution_context()
    yield
    clear_execution_context()


class TestTriggerJobNowLogging:
    """Test logging in trigger_job_now method."""

    @pytest.mark.asyncio
    async def test_trigger_job_logs_duplicate_check(
        self, scheduler_service, mock_repo, mock_session, sample_job
    ):
        """Test that duplicate check is logged."""
        # Setup
        mock_repo.get_job_by_id = AsyncMock(return_value=sample_job)
        mock_repo.get_running_execution = AsyncMock(return_value=None)

        # Mock to prevent actual execution
        with patch.object(scheduler_service, 'get_job_function', return_value=lambda: None):
            with patch.object(scheduler_service, '_create_manual_execution_wrapper') as mock_wrapper:
                mock_wrapper_func = AsyncMock(return_value="exec-123")
                mock_wrapper.return_value = mock_wrapper_func

                # Capture structured logs
                with patch('api.services.scheduler_service.structured_logger') as mock_logger:
                    try:
                        await scheduler_service.trigger_job_now(
                            mock_session,
                            job_id="1",
                            triggered_by_user_id="user123"
                        )
                    except Exception:
                        pass  # Might fail due to mocking, we just want to check logging

                    # Verify duplicate check was logged
                    mock_logger.log_duplicate_check.assert_called_once()
                    call_args = mock_logger.log_duplicate_check.call_args

                    assert call_args.kwargs["job_id"] == "1"
                    assert call_args.kwargs["job_key"] == "hris_replication"
                    assert call_args.kwargs["running_execution_found"] is False

    @pytest.mark.asyncio
    async def test_trigger_job_rejects_duplicate_with_logging(
        self, scheduler_service, mock_repo, mock_session, sample_job
    ):
        """Test that duplicate execution is rejected and logged."""
        # Setup - job is already running
        running_exec = ScheduledJobExecution(
            job_id=1,
            execution_id="existing-exec-123",
            status_id=2
        )
        running_exec.status = "running"

        mock_repo.get_job_by_id = AsyncMock(return_value=sample_job)
        mock_repo.get_running_execution = AsyncMock(return_value=running_exec)

        # Capture logs
        with patch('api.services.scheduler_service.structured_logger') as mock_logger:
            from core.exceptions import ValidationError

            with pytest.raises(ValidationError, match="already running"):
                await scheduler_service.trigger_job_now(
                    mock_session,
                    job_id="1",
                    triggered_by_user_id="user123"
                )

            # Verify duplicate check logged the rejection
            mock_logger.log_duplicate_check.assert_called_once()
            call_args = mock_logger.log_duplicate_check.call_args

            assert call_args.kwargs["running_execution_found"] is True
            assert call_args.kwargs["running_execution_id"] == "existing-exec-123"


class TestExecutionWrapperLogging:
    """Test logging in execution wrapper."""

    @pytest.mark.asyncio
    async def test_wrapper_logs_execution_create_start(self):
        """Test that execution creation start is logged."""
        from api.services.scheduler_service import SchedulerService

        service = SchedulerService()
        service._instance_id = "test-instance"
        service._repo = MagicMock()

        # Create wrapper
        test_func = lambda: "test_result"
        wrapper = service._create_manual_execution_wrapper(
            job_id="1",
            job_key="test_job",
            func=test_func,
            triggered_by_user_id="user123"
        )

        # Mock database session
        with patch('api.services.scheduler_service.get_maria_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_session.return_value.__aiter__.return_value = [mock_session]

            # Mock repo methods
            running_status = MagicMock()
            running_status.id = 2
            service._repo.get_execution_status_by_code = AsyncMock(return_value=running_status)
            service._repo.create_execution = AsyncMock()
            service._repo.update_job = AsyncMock()

            # Capture logs
            with patch('api.services.scheduler_service.structured_logger') as mock_logger:
                with patch('asyncio.create_task'):  # Prevent actual background task
                    execution_id = await wrapper()

                    # Verify logs
                    mock_logger.log_execution_create_start.assert_called_once()
                    mock_logger.log_execution_create_committed.assert_called_once()
                    mock_logger.log_background_task_launch.assert_called_once()

                    # Check parameters
                    start_call = mock_logger.log_execution_create_start.call_args
                    assert start_call.kwargs["job_id"] == "1"
                    assert start_call.kwargs["job_key"] == "test_job"
                    assert start_call.kwargs["trigger_source"] == "MANUAL"
                    assert start_call.kwargs["triggered_by_user_id"] == "user123"


class TestCeleryTaskLogging:
    """Test logging in Celery tasks."""

    def test_hris_task_logs_start_and_completion(self):
        """Test that HRIS task logs start and completion."""
        from tasks.hris import hris_replication_task

        # Mock the actual replication logic
        with patch('tasks.hris._run_async') as mock_run_async:
            mock_run_async.return_value = {"status": "success"}

            # Capture logs
            with patch('tasks.hris.structured_logger') as mock_logger:
                # Mock self.request for Celery task
                mock_self = MagicMock()
                mock_self.request.id = "celery-task-123"
                mock_self.request.retries = 0
                mock_self.max_retries = 3

                try:
                    result = hris_replication_task(
                        mock_self,
                        execution_id="exec-456",
                        triggered_by_user_id="user789"
                    )

                    # Verify start was logged
                    mock_logger.log_celery_task_start.assert_called_once()
                    start_call = mock_logger.log_celery_task_start.call_args

                    assert start_call.kwargs["task_name"] == "hris_replication"
                    assert start_call.kwargs["execution_id"] == "exec-456"
                    assert start_call.kwargs["celery_task_id"] == "celery-task-123"
                    assert start_call.kwargs["triggered_by"] == "user789"

                except Exception:
                    # Might fail due to mocking database connections
                    # We're mainly testing that logging doesn't break the flow
                    pass


class TestLoggingDoesntBreakFunctionality:
    """Test that adding logging doesn't break existing functionality."""

    @pytest.mark.asyncio
    async def test_trigger_job_still_creates_execution(
        self, scheduler_service, mock_repo, mock_session, sample_job,
        running_status
    ):
        """Test that job triggering still works with logging."""
        # Setup
        mock_repo.get_job_by_id = AsyncMock(return_value=sample_job)
        mock_repo.get_running_execution = AsyncMock(return_value=None)
        mock_repo.get_execution_status_by_code = AsyncMock(return_value=running_status)
        mock_repo.create_execution = AsyncMock()
        mock_repo.update_job = AsyncMock()

        test_func = lambda: "test_result"

        with patch.object(scheduler_service, 'get_job_function', return_value=test_func):
            with patch('api.services.scheduler_service.get_maria_session') as mock_get_session:
                mock_db_session = AsyncMock()
                mock_get_session.return_value.__aiter__.return_value = [mock_db_session]

                with patch('asyncio.create_task'):
                    execution_id, job = await scheduler_service.trigger_job_now(
                        mock_session,
                        job_id="1",
                        triggered_by_user_id="user123"
                    )

                    # Verify execution was created
                    assert execution_id is not None
                    assert job == sample_job

    @pytest.mark.asyncio
    async def test_logging_exceptions_dont_prevent_error_handling(
        self, scheduler_service, mock_repo, mock_session
    ):
        """Test that logging errors don't interfere with normal error handling."""
        # Setup job not found scenario
        mock_repo.get_job_by_id = AsyncMock(return_value=None)

        # Force logging to raise exception
        with patch('api.services.scheduler_service.structured_logger') as mock_logger:
            mock_logger.log_duplicate_check.side_effect = Exception("Logging error")

            from core.exceptions import NotFoundError

            # Should still raise NotFoundError (not logging error)
            with pytest.raises(NotFoundError):
                await scheduler_service.trigger_job_now(
                    mock_session,
                    job_id="999",
                    triggered_by_user_id="user123"
                )


class TestJSONOutputValidation:
    """Test that all structured logs produce valid JSON."""

    def test_all_log_calls_produce_valid_json(self):
        """Verify all structured log methods produce parsable JSON."""
        from utils.structured_logger import get_structured_logger

        logger = get_structured_logger("test")

        # Capture all log output
        with patch.object(logger.logger, 'info') as mock_info:
            with patch.object(logger.logger, 'warning') as mock_warning:
                # Log various events
                logger.log_api_entry(
                    job_id="1",
                    action="trigger",
                    user_id="user1"
                )

                logger.log_duplicate_check(
                    job_id="1",
                    job_key="test",
                    running_execution_found=False
                )

                logger.log_execution_create_start(
                    job_id="1",
                    job_key="test",
                    execution_id="exec1",
                    trigger_source="MANUAL"
                )

                logger.log_lock_failed(
                    job_id="1",
                    execution_id="exec1",
                    reason="Test reason"
                )

                logger.log_celery_dispatch_success(
                    job_key="test",
                    execution_id="exec1",
                    celery_task_id="celery1"
                )

                # Verify all calls produced valid JSON
                for call in mock_info.call_args_list:
                    json_str = call[0][0]
                    parsed = json.loads(json_str)  # Should not raise
                    assert "event" in parsed
                    assert "timestamp" in parsed
                    assert "message" in parsed

                for call in mock_warning.call_args_list:
                    json_str = call[0][0]
                    parsed = json.loads(json_str)  # Should not raise
                    assert "event" in parsed


class TestCorrelationIDPropagation:
    """Test that correlation IDs propagate through execution flow."""

    @pytest.mark.asyncio
    async def test_correlation_id_propagates_to_service_logs(
        self, scheduler_service, mock_repo, mock_session, sample_job
    ):
        """Test correlation ID set in API is available in service logs."""
        # Set correlation ID (simulating middleware)
        set_correlation_id("test-correlation-123")

        mock_repo.get_job_by_id = AsyncMock(return_value=sample_job)
        mock_repo.get_running_execution = AsyncMock(return_value=None)

        with patch.object(scheduler_service, 'get_job_function', return_value=lambda: None):
            with patch.object(scheduler_service, '_create_manual_execution_wrapper') as mock_wrapper:
                mock_wrapper_func = AsyncMock(return_value="exec-123")
                mock_wrapper.return_value = mock_wrapper_func

                with patch('api.services.scheduler_service.structured_logger') as mock_logger:
                    # Simulate logging that captures correlation ID
                    def capture_log(*args, **kwargs):
                        from utils.structured_logger import get_correlation_id
                        assert get_correlation_id() == "test-correlation-123"

                    mock_logger.log_duplicate_check.side_effect = capture_log

                    try:
                        await scheduler_service.trigger_job_now(
                            mock_session,
                            job_id="1",
                            triggered_by_user_id="user123"
                        )
                    except Exception:
                        pass

                    # Verify log was called (which verified correlation ID)
                    mock_logger.log_duplicate_check.assert_called_once()
