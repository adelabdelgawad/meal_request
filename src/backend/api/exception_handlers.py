"""
Exception Handlers - Maps domain exceptions to HTTP responses.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from core.exceptions import (
    DomainException,
    NotFoundError,
    ConflictError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
)


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """Handle general domain exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_type": exc.__class__.__name__},
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle NotFoundError (404)."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": str(exc),
            "error_type": "NotFoundError",
            "entity": exc.entity if hasattr(exc, "entity") else None,
        },
    )


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Handle ConflictError (409)."""
    return JSONResponse(
        status_code=409,
        content={
            "detail": str(exc),
            "error_type": "ConflictError",
            "entity": exc.entity if hasattr(exc, "entity") else None,
            "field": exc.field if hasattr(exc, "field") else None,
        },
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle ValidationError (422)."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc),
            "error_type": "ValidationError",
            "errors": exc.errors if hasattr(exc, "errors") else [],
        },
    )


async def authentication_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """Handle AuthenticationError (401)."""
    return JSONResponse(
        status_code=401,
        content={
            "detail": str(exc),
            "error_type": "AuthenticationError",
        },
    )


async def authorization_error_handler(
    request: Request, exc: AuthorizationError
) -> JSONResponse:
    """Handle AuthorizationError (403)."""
    return JSONResponse(
        status_code=403,
        content={
            "detail": str(exc),
            "error_type": "AuthorizationError",
        },
    )


async def database_error_handler(
    request: Request, exc: DatabaseError
) -> JSONResponse:
    """Handle DatabaseError (500)."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Database operation failed. Please try again later.",
            "error_type": "DatabaseError",
        },
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app."""
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ConflictError, conflict_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
