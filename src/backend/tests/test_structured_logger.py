"""
Unit tests for structured logging utility.

Tests correlation IDs, execution context, timestamp tracking,
and JSON output formatting.
"""

import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from utils.structured_logger import (
    StructuredLogger,
    get_structured_logger,
    set_correlation_id,
    get_correlation_id,
    set_execution_context,
    get_execution_context,
    clear_execution_context
)


class TestCorrelationID:
    """Test correlation ID context management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and retrieving correlation ID."""
        test_id = "test-correlation-123"
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

    def test_generate_correlation_id_if_none(self):
        """Test auto-generation of correlation ID."""
        generated_id = set_correlation_id(None)
        assert generated_id is not None
        assert len(generated_id) == 36  # UUID format
        assert get_correlation_id() == generated_id


class TestExecutionContext:
    """Test execution context management."""

    def teardown_method(self):
        """Clear execution context after each test."""
        clear_execution_context()

    def test_set_and_get_execution_context(self):
        """Test setting and retrieving execution context."""
        context = {"job_id": "123", "execution_id": "abc", "user_id": "user1"}
        set_execution_context(**context)

        retrieved = get_execution_context()
        assert retrieved == context

    def test_update_execution_context(self):
        """Test updating existing execution context."""
        set_execution_context(job_id="123", user_id="user1")
        set_execution_context(execution_id="abc")

        context = get_execution_context()
        assert context == {"job_id": "123", "user_id": "user1", "execution_id": "abc"}

    def test_clear_execution_context(self):
        """Test clearing execution context."""
        set_execution_context(job_id="123")
        clear_execution_context()
        assert get_execution_context() == {}


class TestStructuredLogger:
    """Test StructuredLogger functionality."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def structured_logger(self, mock_logger):
        """Create a StructuredLogger instance with mock logger."""
        return StructuredLogger(mock_logger)

    def teardown_method(self):
        """Clear context after each test."""
        clear_execution_context()

    def test_build_log_entry_basic(self, structured_logger, mock_logger):
        """Test basic log entry construction."""
        entry = structured_logger._build_log_entry(
            event="TEST_EVENT",
            level="INFO",
            message="Test message",
            custom_field="custom_value"
        )

        assert entry["event"] == "TEST_EVENT"
        assert entry["level"] == "INFO"
        assert entry["message"] == "Test message"
        assert entry["custom_field"] == "custom_value"
        assert "timestamp" in entry
        assert "timestamp_ns" in entry

    def test_build_log_entry_with_correlation_id(self, structured_logger):
        """Test log entry includes correlation ID from context."""
        correlation_id = "test-corr-id"
        set_correlation_id(correlation_id)

        entry = structured_logger._build_log_entry(
            event="TEST",
            level="INFO",
            message="Test"
        )

        assert entry["correlation_id"] == correlation_id

    def test_build_log_entry_with_execution_context(self, structured_logger):
        """Test log entry includes execution context."""
        set_execution_context(job_id="job123", execution_id="exec456")

        entry = structured_logger._build_log_entry(
            event="TEST",
            level="INFO",
            message="Test"
        )

        assert entry["execution_context"]["job_id"] == "job123"
        assert entry["execution_context"]["execution_id"] == "exec456"

    def test_info_log_creates_json(self, structured_logger, mock_logger):
        """Test INFO level logging creates valid JSON."""
        structured_logger.info(
            event="TEST_EVENT",
            message="Test message",
            custom_data={"key": "value"}
        )

        # Verify logger.info was called
        assert mock_logger.info.called
        logged_json = mock_logger.info.call_args[0][0]

        # Verify it's valid JSON
        parsed = json.loads(logged_json)
        assert parsed["event"] == "TEST_EVENT"
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["custom_data"] == {"key": "value"}

    def test_warning_log_creates_json(self, structured_logger, mock_logger):
        """Test WARNING level logging creates valid JSON."""
        structured_logger.warning(
            event="WARNING_EVENT",
            message="Warning message"
        )

        assert mock_logger.warning.called
        logged_json = mock_logger.warning.call_args[0][0]
        parsed = json.loads(logged_json)
        assert parsed["level"] == "WARNING"

    def test_error_log_creates_json(self, structured_logger, mock_logger):
        """Test ERROR level logging creates valid JSON."""
        structured_logger.error(
            event="ERROR_EVENT",
            message="Error message"
        )

        assert mock_logger.error.called
        logged_json = mock_logger.error.call_args[0][0]
        parsed = json.loads(logged_json)
        assert parsed["level"] == "ERROR"

    def test_track_execution_start_and_end(self, structured_logger):
        """Test execution time tracking."""
        execution_id = "exec123"

        # Start tracking
        structured_logger.track_execution_start(execution_id)
        assert execution_id in structured_logger._start_times

        # Simulate some work
        import time
        time.sleep(0.01)  # 10ms

        # End tracking
        duration_ms = structured_logger.track_execution_end(execution_id)

        assert duration_ms is not None
        assert duration_ms >= 10  # At least 10ms
        assert execution_id not in structured_logger._start_times  # Cleaned up

    def test_track_execution_end_without_start(self, structured_logger):
        """Test ending tracking without starting returns None."""
        duration = structured_logger.track_execution_end("nonexistent")
        assert duration is None

    def test_delta_ms_in_log_entry(self, structured_logger, mock_logger):
        """Test delta_ms is calculated and included in log entry."""
        execution_id = "exec123"
        structured_logger.track_execution_start(execution_id)

        import time
        time.sleep(0.01)  # 10ms

        structured_logger.info(
            event="TEST",
            message="Test",
            execution_id=execution_id
        )

        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert "delta_ms" in parsed
        assert parsed["delta_ms"] >= 10

    def test_log_api_entry(self, structured_logger, mock_logger):
        """Test API entry logging."""
        structured_logger.log_api_entry(
            job_id="job123",
            action="trigger",
            user_id="user456"
        )

        assert mock_logger.info.called
        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "API_ENTRY"
        assert parsed["job_id"] == "job123"
        assert parsed["action"] == "trigger"
        assert parsed["user_id"] == "user456"

    def test_log_duplicate_check_passed(self, structured_logger, mock_logger):
        """Test duplicate check logging when no running execution found."""
        structured_logger.log_duplicate_check(
            job_id="job123",
            job_key="hris_replication",
            running_execution_found=False
        )

        assert mock_logger.info.called
        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "DUPLICATE_CHECK_PASSED"
        assert parsed["check_result"] == "PASSED"

    def test_log_duplicate_check_rejected(self, structured_logger, mock_logger):
        """Test duplicate check logging when running execution found."""
        structured_logger.log_duplicate_check(
            job_id="job123",
            job_key="hris_replication",
            running_execution_found=True,
            running_execution_id="exec789"
        )

        assert mock_logger.warning.called
        logged_json = mock_logger.warning.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "DUPLICATE_CHECK_REJECTED"
        assert parsed["check_result"] == "REJECTED"
        assert parsed["running_execution_id"] == "exec789"

    def test_log_execution_create_start(self, structured_logger, mock_logger):
        """Test execution creation start logging."""
        structured_logger.log_execution_create_start(
            job_id="job123",
            job_key="hris_replication",
            execution_id="exec456",
            trigger_source="MANUAL",
            parent_execution_id="parent789"
        )

        assert mock_logger.info.called
        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "EXEC_CREATE_START"
        assert parsed["execution_id"] == "exec456"
        assert parsed["trigger_source"] == "MANUAL"
        assert parsed["lineage"]["parent_execution_id"] == "parent789"

    def test_log_lock_acquired(self, structured_logger, mock_logger):
        """Test lock acquisition logging."""
        structured_logger.log_lock_acquired(
            job_id="job123",
            execution_id="exec456",
            lock_id=789
        )

        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "LOCK_ACQUIRED"
        assert parsed["lock_result"] == "SUCCESS"
        assert parsed["lock_id"] == 789

    def test_log_lock_failed(self, structured_logger, mock_logger):
        """Test lock failure logging."""
        structured_logger.log_lock_failed(
            job_id="job123",
            execution_id="exec456",
            reason="Another instance is running"
        )

        assert mock_logger.warning.called
        logged_json = mock_logger.warning.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "LOCK_FAILED"
        assert parsed["lock_result"] == "FAILED"
        assert parsed["reason"] == "Another instance is running"

    def test_log_celery_dispatch_success(self, structured_logger, mock_logger):
        """Test successful Celery dispatch logging."""
        structured_logger.log_celery_dispatch_success(
            job_key="hris_replication",
            execution_id="exec456",
            celery_task_id="celery123"
        )

        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "CELERY_DISPATCH_SUCCESS"
        assert parsed["dispatch_result"] == "SUCCESS"
        assert parsed["celery_task_id"] == "celery123"

    def test_log_celery_task_complete_with_total_duration(self, structured_logger, mock_logger):
        """Test task completion logging includes total duration."""
        execution_id = "exec456"

        # Start tracking
        structured_logger.track_execution_start(execution_id)

        import time
        time.sleep(0.01)

        # Log completion
        structured_logger.log_celery_task_complete(
            task_name="hris_replication",
            execution_id=execution_id,
            final_status="SUCCESS",
            duration_ms=50.0
        )

        logged_json = mock_logger.info.call_args[0][0]
        parsed = json.loads(logged_json)

        assert parsed["event"] == "CELERY_TASK_COMPLETE"
        assert parsed["task_duration_ms"] == 50.0
        assert "total_duration_ms" in parsed
        assert parsed["total_duration_ms"] >= 10

    def test_datetime_serialization(self, structured_logger, mock_logger):
        """Test datetime objects are properly serialized."""
        structured_logger.info(
            event="TEST",
            message="Test",
            created_at=datetime.now()
        )

        logged_json = mock_logger.info.call_args[0][0]
        # Should not raise json.JSONDecodeError
        parsed = json.loads(logged_json)
        assert "created_at" in parsed


class TestGetStructuredLogger:
    """Test factory function for getting structured logger."""

    def test_get_structured_logger_returns_instance(self):
        """Test factory function returns StructuredLogger instance."""
        logger = get_structured_logger("test_module")
        assert isinstance(logger, StructuredLogger)

    def test_get_structured_logger_uses_correct_logger(self):
        """Test factory function creates logger with correct name."""
        with patch('utils.structured_logger.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            structured_logger = get_structured_logger("test_module")

            mock_get_logger.assert_called_once_with("test_module")
            assert structured_logger.logger == mock_logger


class TestJSONParsability:
    """Test that all logged output is valid JSON."""

    @pytest.fixture
    def structured_logger(self):
        """Create a StructuredLogger with real logger."""
        logger = logging.getLogger("test")
        return StructuredLogger(logger)

    def test_all_log_methods_produce_valid_json(self, structured_logger):
        """Test all logging methods produce parsable JSON."""
        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_api_entry(
                job_id="123",
                action="trigger",
                user_id="user1"
            )
            json.loads(mock_info.call_args[0][0])  # Should not raise

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_duplicate_check(
                job_id="123",
                job_key="test",
                running_execution_found=False
            )
            json.loads(mock_info.call_args[0][0])

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_execution_create_start(
                job_id="123",
                job_key="test",
                execution_id="exec1",
                trigger_source="MANUAL"
            )
            json.loads(mock_info.call_args[0][0])

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_background_task_launch(
                job_id="123",
                job_key="test",
                execution_id="exec1"
            )
            json.loads(mock_info.call_args[0][0])

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_lock_acquired(
                job_id="123",
                execution_id="exec1",
                lock_id=1
            )
            json.loads(mock_info.call_args[0][0])

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_celery_dispatch_success(
                job_key="test",
                execution_id="exec1",
                celery_task_id="celery1"
            )
            json.loads(mock_info.call_args[0][0])

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_celery_task_start(
                task_name="test_task",
                execution_id="exec1",
                celery_task_id="celery1",
                worker_host="localhost"
            )
            json.loads(mock_info.call_args[0][0])

        with patch.object(structured_logger.logger, 'info') as mock_info:
            structured_logger.log_celery_task_complete(
                task_name="test_task",
                execution_id="exec1",
                final_status="SUCCESS",
                duration_ms=100.0
            )
            json.loads(mock_info.call_args[0][0])
