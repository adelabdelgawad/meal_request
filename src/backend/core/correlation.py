"""Correlation ID middleware and utilities for request tracing.

This module provides middleware for generating and propagating correlation IDs
throughout the request lifecycle. Correlation IDs link related operations together
for debugging and auditing purposes.
"""

import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get the current request's correlation ID.

    Returns the correlation ID from the current request context.
    If no correlation ID has been set, generates and returns a new UUID.

    This function can be called from anywhere in the request context,
    including services, repositories, and background tasks.

    Returns:
        str: The correlation ID as a UUID string

    Example:
        from core.correlation import get_correlation_id

        # In a controller or service
        correlation_id = get_correlation_id()
        await audit_service.log_action(..., correlation_id=correlation_id)
    """
    current_id = correlation_id_var.get()
    if not current_id:
        current_id = str(uuid.uuid4())
        correlation_id_var.set(current_id)
    return current_id


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current request context.

    This is typically called by the middleware, but can also be used
    in tests or when propagating correlation IDs to background tasks.

    Args:
        correlation_id: The correlation ID to set

    Example:
        from core.correlation import set_correlation_id

        # In a Celery task that receives correlation_id from parent request
        set_correlation_id(task_kwargs["correlation_id"])
    """
    correlation_id_var.set(correlation_id)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to all requests.

    This middleware:
    1. Checks for an existing correlation ID in the X-Correlation-ID header
    2. Generates a new UUID if none exists
    3. Stores it in async-safe context storage
    4. Adds it to the response headers

    Usage:
        from core.correlation import CorrelationMiddleware

        app = FastAPI()
        app.add_middleware(CorrelationMiddleware)

    The middleware must be registered BEFORE authentication and other
    middleware that might need to log with correlation IDs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID.

        Args:
            request: The incoming request
            call_next: The next middleware/route handler

        Returns:
            Response: The response with correlation ID header added
        """
        correlation_id = request.headers.get("X-Correlation-ID")

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        set_correlation_id(correlation_id)

        response = await call_next(request)

        response.headers["X-Correlation-ID"] = correlation_id

        return response
