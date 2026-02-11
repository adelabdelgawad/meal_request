import logging
import sys
from typing import Callable

# Import unified API routers from new router structure
from api.routers import main_router, analytics_router_legacy
from core.config import settings
from core.correlation import CorrelationMiddleware
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    AuditWriteError,
    ConflictError,
    DatabaseError,
    DetailedHTTPException,
    DomainException,
    NotFoundError,
    OperationalLogWriteError,
    ValidationError,
)
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from utils.observability import init_observability
from utils.security import RateLimitExceeded, _rate_limit_exceeded_handler, limiter
from utils.startup import lifespan

# Load environment variables from .env file
load_dotenv()

# Configure structured JSON logging
# JSON format enables better log querying in production observability tools
try:
    from pythonjsonlogger.json import JsonFormatter

    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False

_log_handler = logging.StreamHandler(sys.stdout)
if HAS_JSON_LOGGER and settings.environment == "production":
    _log_handler.setFormatter(
        JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level"},
        )
    )
else:
    _log_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

logging.basicConfig(
    level=logging.INFO,
    handlers=[_log_handler],
    force=True,  # Force reconfiguration of root logger
)

# Set the root logger level explicitly
logging.getLogger().setLevel(logging.INFO)

# Suppress noisy libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

# Initialize the FastAPI app with custom lifespan
# Enable camelCase serialization for all response models
app = FastAPI(
    lifespan=lifespan,
    # Return camelCase aliases in responses (matches CamelModel schema)
    response_model_by_alias=True,
)

# Initialize observability (Prometheus metrics and OpenTelemetry tracing)
init_observability(app)

# Register correlation middleware BEFORE CORS middleware
app.add_middleware(CorrelationMiddleware)


@app.middleware("http")
async def security_headers_middleware(
    request: Request, call_next: Callable
) -> Response:
    """
    Add security headers to all responses.

    Security headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: restricts access to sensitive APIs
    - Strict-Transport-Security (HSTS) in production only
    """
    response = await call_next(request)

    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions-Policy - restrict access to sensitive APIs
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    )

    # HSTS only in production
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return response


# Configure CORS from environment settings
allow_origins = settings.api.cors_origins or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Request-ID",
        "X-CSRF-Token",
        "X-Device-Fingerprint",
        "Accept",
        "Accept-Language",
    ],
)

logger.info(
    "CORS middleware configured",
    extra={
        "allowed_origins": allow_origins,
        "origin_count": len(allow_origins),
    },
)


# Exception handlers


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    """Handle general domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc), "error_type": exc.__class__.__name__},
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle NotFoundError (404)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_type": "NotFoundError",
        },
    )


async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    """Handle ConflictError (409)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_type": "ConflictError",
        },
    )


async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle ValidationError (422)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_type": "ValidationError",
        },
    )


async def authentication_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """Handle AuthenticationError (401)."""
    return JSONResponse(
        status_code=exc.status_code,
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
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_type": "AuthorizationError",
        },
    )


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle DatabaseError (500)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": "Database operation failed. Please try again later.",
            "error_type": "DatabaseError",
        },
    )


async def audit_write_error_handler(
    request: Request, exc: AuditWriteError
) -> JSONResponse:
    """Handle AuditWriteError (503)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_type": "AuditWriteError",
        },
    )


async def operational_log_write_error_handler(
    request: Request, exc: OperationalLogWriteError
) -> JSONResponse:
    """Handle OperationalLogWriteError (500)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc),
            "error_type": "OperationalLogWriteError",
        },
    )


async def detailed_http_exception_handler(
    request: Request, exc: DetailedHTTPException
) -> JSONResponse:
    """Handle DetailedHTTPException with development stack traces."""
    content = {
        "detail": exc.detail,
        "error_type": "DetailedHTTPException",
    }

    # Add stack trace and context in development mode
    if settings.environment == "local" or settings.environment == "development":
        if exc.stack_trace:
            content["stack_trace"] = exc.stack_trace
        if exc.context:
            content["context"] = exc.context

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
    )


# Register exception handlers
app.add_exception_handler(NotFoundError, not_found_handler)
app.add_exception_handler(ConflictError, conflict_handler)
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(AuthenticationError, authentication_error_handler)
app.add_exception_handler(AuthorizationError, authorization_error_handler)
app.add_exception_handler(DatabaseError, database_error_handler)
app.add_exception_handler(AuditWriteError, audit_write_error_handler)
app.add_exception_handler(OperationalLogWriteError, operational_log_write_error_handler)
app.add_exception_handler(DetailedHTTPException, detailed_http_exception_handler)
app.add_exception_handler(DomainException, domain_exception_handler)


# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint including Redis and Database status.

    Returns:
        dict: Health status of application components
    """
    import time

    from core.redis import is_redis_available, redis_health_check
    from db.database import engine
    from core.config import settings

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "application": {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.environment,
        },
        "redis": {
            "status": "unavailable",
            "error": "Redis not configured or not enabled",
        },
        "database": {
            "status": "unknown",
            "note": "Database health check not implemented",
        },
    }

    # Check Redis health if enabled
    if settings.redis.enabled and is_redis_available():
        try:
            redis_health = await redis_health_check()
            health_status["redis"] = {
                "status": redis_health["status"],
                "latency_ms": redis_health.get("latency_ms"),
                "redis_version": redis_health.get("redis_version"),
                "uptime_seconds": redis_health.get("uptime_seconds"),
                "connected_clients": redis_health.get("connected_clients"),
                "memory_usage": {
                    "used_memory_mb": redis_health.get("memory", {}).get(
                        "used_memory_mb"
                    ),
                    "used_memory_percent": redis_health.get("memory", {}).get(
                        "used_memory_percent"
                    ),
                },
                "performance": {
                    "keyspace_hit_rate": redis_health.get("performance", {}).get(
                        "keyspace_hit_rate"
                    ),
                    "ops_per_sec": redis_health.get("performance", {}).get(
                        "instantaneous_ops_per_sec"
                    ),
                },
                "circuit_breaker": redis_health.get("circuit_breaker", {}),
            }
        except Exception as e:
            health_status["redis"] = {"status": "unhealthy", "error": str(e)}

    # Determine overall health
    if health_status["redis"]["status"] in ["unhealthy", "unavailable"]:
        # Redis is critical for most functionality
        health_status["status"] = "degraded"

    return health_status


@app.get("/health/redis")
async def redis_health_endpoint():
    """
    Dedicated Redis health check endpoint.

    Returns:
        dict: Detailed Redis health information
    """
    from core.redis import get_redis_config, redis_health_check

    redis_health = await redis_health_check()

    # Add configuration info if Redis is healthy
    if redis_health["status"] == "healthy":
        config = await get_redis_config()
        redis_health["configuration"] = config

    return redis_health


@app.get("/health/metrics")
async def get_application_metrics():
    """
    Application metrics endpoint (JSON format for monitoring).

    Returns:
        dict: Application and Redis metrics in JSON format
    """
    from core.redis import get_cache_stats

    metrics = {
        "application_info": {"version": "1.0.0", "environment": settings.environment}
    }

    # Add Redis metrics if available
    if settings.redis.enabled:
        try:
            cache_stats = await get_cache_stats()
            metrics["redis_metrics"] = cache_stats
        except Exception as e:
            metrics["redis_metrics"] = {"error": str(e)}

    return metrics


# Include unified routers with prefixes matching frontend API structure
logger.info("Registering API routers")
app.include_router(main_router, prefix="/api/v1")
# Analytics router mounted at /api for frontend compatibility
app.include_router(analytics_router_legacy, prefix="/api")
