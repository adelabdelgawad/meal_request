"""
Domain-level exceptions for the application.

These exceptions represent domain/business logic errors and are mapped to HTTP responses
via the exception handler in api/exception_handlers.py.
"""

from typing import Any, Dict, List, Optional


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


class NotFoundError(DomainException):
    """
    Raised when a requested resource is not found.
    Maps to HTTP 404 Not Found.
    """

    def __init__(
        self,
        entity: str,
        identifier: Any,
        message: Optional[str] = None,
    ):
        """
        Initialize NotFoundError.

        Args:
            entity: The entity type that was not found (e.g., "User", "MealRequest")
            identifier: The identifier used in the query (e.g., user ID, username)
            message: Optional custom message. If not provided, generates a default.
        """
        self.entity = entity
        self.identifier = identifier

        if message is None:
            message = f"{entity} with identifier '{identifier}' not found"

        super().__init__(message)


class ConflictError(DomainException):
    """
    Raised when a unique constraint is violated.
    Maps to HTTP 409 Conflict.
    """

    def __init__(
        self,
        entity: str,
        field: str,
        value: Any,
        message: Optional[str] = None,
    ):
        """
        Initialize ConflictError.

        Args:
            entity: The entity type (e.g., "User", "MealRequest")
            field: The field that caused the conflict (e.g., "username", "email")
            value: The value that caused the conflict
            message: Optional custom message. If not provided, generates a default.
        """
        self.entity = entity
        self.field = field
        self.value = value

        if message is None:
            message = (
                f"{entity} with {field}='{value}' already exists. "
                f"Please use a unique {field}."
            )

        super().__init__(message)


class ValidationError(DomainException):
    """
    Raised when input validation fails.
    Maps to HTTP 422 Unprocessable Entity.
    """

    def __init__(
        self,
        errors: List[Dict[str, Any]],
        message: Optional[str] = None,
    ):
        """
        Initialize ValidationError.

        Args:
            errors: List of error dicts with structure: [{"field": "username", "message": "..."}]
            message: Optional custom message. If not provided, generates a default.
        """
        self.errors = errors

        if message is None:
            message = f"Validation failed: {len(errors)} error(s)"

        super().__init__(message)


class AuthenticationError(DomainException):
    """
    Raised when authentication fails.
    Maps to HTTP 401 Unauthorized.
    """

    def __init__(self, message: str = "Authentication failed"):
        """Initialize AuthenticationError."""
        super().__init__(message)


class AuthorizationError(DomainException):
    """
    Raised when user lacks required permissions.
    Maps to HTTP 403 Forbidden.
    """

    def __init__(self, message: str = "Insufficient permissions"):
        """Initialize AuthorizationError."""
        super().__init__(message)


class DatabaseError(DomainException):
    """
    Raised when a database operation fails.
    Maps to HTTP 500 Internal Server Error.
    """

    def __init__(self, message: str = "Database operation failed"):
        """Initialize DatabaseError."""
        super().__init__(message)
