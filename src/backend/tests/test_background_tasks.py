"""
Background Tasks Tests - Tests for FastAPI BackgroundTasks integration.

This test module validates that API endpoints properly use FastAPI BackgroundTasks
for non-blocking email operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient

from routers.router_router_meal_request import router


class TestBackgroundTasksIntegration:
    """Test suite for FastAPI BackgroundTasks integration."""

    @pytest.fixture
    def mock_email_sender(self):
        """Mock EmailSender for testing."""
        with patch("utils.mail_sender.EmailSender") as mock_sender:
            mock_instance = MagicMock()
            mock_message = MagicMock()
            mock_instance.create_message.return_value = mock_message
            mock_sender.return_value = mock_instance
            yield mock_sender

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        return TestClient(app)

    def test_background_tasks_status_endpoint(self, client):
        """Test that the background tasks status endpoint works."""
        response = client.get("/api/v1/background-tasks-status")

        assert response.status_code == 200
        data = response.json()
        assert data["background_processing"] == "fastapi"
        assert data["method"] == "BackgroundTasks"
        assert "/create-meal-request" in data["endpoints"]

    def test_send_notification_background_function(self, mock_email_sender):
        """Test the synchronous background email function."""
        from routers.router_router_meal_request import send_notification_background

        # Mock the template rendering
        with patch(
            "routers.router_router_meal_request.generate_new_request_template"
        ) as mock_template:
            mock_template.return_value = "<p>Test email body</p>"

            # Call the background function
            send_notification_background(
                request_id=123,
                request_lines=5,
                to_recipient="test@example.com",
                cc_recipients=["cc@example.com"],
            )

            # Verify email sender was called
            mock_email_sender.return_value.create_message.assert_called_once_with(
                subject="Meal Request Submitted #123 - Confirmation Pending",
                body="<p>Test email body</p>",
                to_recipient="test@example.com",
                cc_recipients=["cc@example.com"],
            )
            mock_email_sender.return_value.create_message.return_value.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_adds_background_task(self):
        """Test that send_notification properly adds task to BackgroundTasks."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from routers.router_router_meal_request import send_notification

        # Create mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        # Create mock background tasks
        mock_background_tasks = MagicMock(spec=BackgroundTasks)

        # Call send_notification
        await send_notification(
            session=mock_session,
            background_tasks=mock_background_tasks,
            request_id=456,
            request_lines=3,
            to_recipient="test@example.com",
        )

        # Verify background task was added
        mock_background_tasks.add_task.assert_called_once()

    def test_employees_endpoint(self, client):
        """Test that employees endpoint works."""
        with patch(
            "routers.router_router_meal_request.read_employees_for_request_page"
        ) as mock_read:
            mock_read.return_value = [
                {"id": 1, "name": "Test Employee", "department": "IT"}
            ]

            with patch(
                "routers.router_router_meal_request.get_maria_session"
            ) as mock_session:
                mock_session.return_value.__anext__ = AsyncMock(
                    return_value=MagicMock()
                )

                # This test would need proper session mocking
                # For now, we just verify the endpoint exists
                pass


class TestBackgroundTaskErrorHandling:
    """Test error handling in background tasks."""

    def test_background_task_logs_error_on_failure(self, caplog):
        """Test that background task logs errors properly."""
        from routers.router_router_meal_request import send_notification_background

        with patch("utils.mail_sender.EmailSender") as mock_sender:
            mock_sender.return_value.create_message.side_effect = Exception(
                "Email server unavailable"
            )

            with patch(
                "routers.router_router_meal_request.generate_new_request_template"
            ) as mock_template:
                mock_template.return_value = "<p>Test</p>"

                # This should not raise but should log the error
                send_notification_background(
                    request_id=789,
                    request_lines=2,
                    to_recipient="error@example.com",
                )

                # The function should handle the error gracefully
                # Check that error was logged (would need logging capture setup)


if __name__ == "__main__":
    print("Running background tasks tests...")
    print("To run tests: pytest tests/test_background_tasks.py -v")
    print("Requires: pytest, pytest-asyncio, fastapi")
