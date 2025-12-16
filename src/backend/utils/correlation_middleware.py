"""
Correlation ID middleware for FastAPI.

Automatically assigns and tracks correlation IDs for all HTTP requests,
enabling end-to-end tracing of request flows through the system.
"""

import logging
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from utils.structured_logger import set_correlation_id, get_correlation_id

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds correlation ID to every request.

    Features:
    - Generates new correlation ID for each request (or uses existing from header)
    - Sets correlation ID in context for async access
    - Adds correlation ID to response headers
    - Logs request entry/exit with correlation ID
    """

    CORRELATION_ID_HEADER = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and inject correlation ID.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with correlation ID header
        """
        # Get correlation ID from request header or generate new one
        correlation_id = request.headers.get(self.CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid4())

        # Set in context for access throughout request lifecycle
        set_correlation_id(correlation_id)

        # Log request entry
        logger.debug(
            f"[{correlation_id}] {request.method} {request.url.path} - Request started"
        )

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[self.CORRELATION_ID_HEADER] = correlation_id

            # Log request completion
            logger.debug(
                f"[{correlation_id}] {request.method} {request.url.path} - "
                f"Response {response.status_code}"
            )

            return response

        except Exception as e:
            # Log error with correlation ID
            logger.error(
                f"[{correlation_id}] {request.method} {request.url.path} - "
                f"Error: {str(e)}"
            )
            raise
