"""
Domain-level exceptions for the application.

Simple exceptions with message-only constructors.
"""

from typing import Any, Dict, List, Optional

from fastapi import status


class DomainException(Exception):
    """
    Base domain exception.

    All domain exceptions inherit from this class and are caught by exception handlers
    to be mapped to appropriate HTTP response codes.
    """

    def __init__(self, message: str):
        """Initialize exception with message."""
        self.message = message
        super().__init__(self.message)

    @property
    def status_code(self) -> int:
        """HTTP status code for this exception."""
        return status.HTTP_500_INTERNAL_SERVER_ERROR


class NotFoundError(DomainException):
    """
    Raised when a requested resource is not found.
    Maps to HTTP 404 Not Found.
    """

    def __init__(self, message: str):
        """Initialize NotFoundError with message."""
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return status.HTTP_404_NOT_FOUND


class ConflictError(DomainException):
    """
    Raised when a unique constraint is violated.
    Maps to HTTP 409 Conflict.
    """

    def __init__(self, message: str):
        """Initialize ConflictError with message."""
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return status.HTTP_409_CONFLICT


class ValidationError(DomainException):
    """
    Raised when input validation fails.
    Maps to HTTP 422 Unprocessable Entity.
    """

    def __init__(self, message: str):
        """Initialize ValidationError with message."""
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return status.HTTP_422_UNPROCESSABLE_ENTITY


class AuthenticationError(DomainException):
    """
    Raised when authentication fails.
    Maps to HTTP 401 Unauthorized.
    """

    def __init__(self, message: str = "Authentication failed"):
        """Initialize AuthenticationError."""
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return status.HTTP_401_UNAUTHORIZED


class AuthorizationError(DomainException):
    """
    Raised when user lacks required permissions.
    Maps to HTTP 403 Forbidden.
    """

    def __init__(self, message: str = "Insufficient permissions"):
        """Initialize AuthorizationError."""
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return status.HTTP_403_FORBIDDEN


class DatabaseError(DomainException):
    """
    Raised when a database operation fails.
    Maps to HTTP 500 Internal Server Error.
    """

    def __init__(self, message: str = "Database operation failed"):
        """Initialize DatabaseError."""
        super().__init__(message)


class AuditWriteError(DomainException):
    """
    Raised when audit log write fails.

    In strict compliance mode, this exception should block the original operation
    from completing to ensure all actions are properly audited.

    Usage:
        try:
            await audit_service.log_action(...)
        except AuditWriteError:
            raise HTTPException(503, "Operation blocked: audit system unavailable")
    """

    def __init__(self, message: str = "Audit log write failed"):
        """Initialize AuditWriteError."""
        super().__init__(message)

    @property
    def status_code(self) -> int:
        return status.HTTP_503_SERVICE_UNAVAILABLE


class OperationalLogWriteError(DomainException):
    """
    Raised when operational log write fails.

    Unlike AuditWriteError, this does not block operations but indicates
    a logging system issue that should be monitored.
    """

    def __init__(self, message: str = "Operational log write failed"):
        """Initialize OperationalLogWriteError."""
        super().__init__(message)


class DetailedHTTPException(Exception):
    """
    Detailed HTTP exception with stack traces for development.

    Used in development mode to provide additional debugging information.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize DetailedHTTPException.

        Args:
            status_code: HTTP status code
            detail: Error detail message
            stack_trace: Optional stack trace string
            context: Optional additional context information
        """
        self.status_code = status_code
        self.detail = detail
        self.stack_trace = stack_trace
        self.context = context or {}
        super().__init__(detail)
