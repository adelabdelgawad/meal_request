import logging
import sys

# Import analytics router
from api.analytics import router as analytics_router
# Import exception handlers
from api.exception_handlers import register_exception_handlers
# Import unified API v1 routers
from api.v1 import (admin, analysis, audit, auth, departments, domain_users,
                    employees, hris, internal_auth, login, me, meal_requests,
                    meal_types, navigation, permissions, reporting, requests,
                    scheduler)
from api.v1 import settings as settings_router
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from settings import settings
from utils.observability import init_observability
from utils.security import (RateLimitExceeded, _rate_limit_exceeded_handler,
                            limiter)
from utils.startup import lifespan

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],  # Explicitly set handler
    force=True,  # Force reconfiguration of root logger
)

# Set the root logger level explicitly
logging.getLogger().setLevel(logging.INFO)


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

# Configure CORS from environment settings
allow_origins = settings.ALLOWED_ORIGINS or ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

logger.info(
    "CORS middleware configured",
    extra={
        "allowed_origins": allow_origins,
        "origin_count": len(allow_origins),
    },
)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register domain exception handlers
register_exception_handlers(app)


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint including Redis status.

    Returns:
        dict: Health status of application components
    """
    import time

    from core.redis import is_redis_available, redis_health_check
    from settings import settings

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "application": {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        },
        "redis": {
            "status": "unavailable",
            "error": "Redis not configured or not enabled"
        },
        "database": {
            "status": "unknown",
            "note": "Database health check not implemented"
        }
    }

    # Check Redis health if enabled
    if settings.REDIS_ENABLED and is_redis_available():
        try:
            redis_health = await redis_health_check()
            health_status["redis"] = {
                "status": redis_health["status"],
                "latency_ms": redis_health.get("latency_ms"),
                "redis_version": redis_health.get("redis_version"),
                "uptime_seconds": redis_health.get("uptime_seconds"),
                "connected_clients": redis_health.get("connected_clients"),
                "memory_usage": {
                    "used_memory_mb": redis_health.get("memory", {}).get("used_memory_mb"),
                    "used_memory_percent": redis_health.get("memory", {}).get("used_memory_percent")
                },
                "performance": {
                    "keyspace_hit_rate": redis_health.get("performance", {}).get("keyspace_hit_rate"),
                    "ops_per_sec": redis_health.get("performance", {}).get("instantaneous_ops_per_sec")
                },
                "circuit_breaker": redis_health.get("circuit_breaker", {})
            }
        except Exception as e:
            health_status["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }

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
    from settings import settings

    metrics = {
        "application_info": {
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }
    }

    # Add Redis metrics if available
    if settings.REDIS_ENABLED:
        try:
            cache_stats = await get_cache_stats()
            metrics["redis_metrics"] = cache_stats
        except Exception as e:
            metrics["redis_metrics"] = {"error": str(e)}

    return metrics


# Include unified API v1 routers
logger.info("Registering API v1 routers")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(login.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(navigation.router, prefix="/api/v1")
app.include_router(meal_requests.router, prefix="/api/v1")
app.include_router(meal_types.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(reporting.router, prefix="/api/v1")
app.include_router(internal_auth.router, prefix="/api/v1")
app.include_router(domain_users.router, prefix="/api/v1")
app.include_router(scheduler.router, prefix="/api/v1")
app.include_router(hris.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
# Include analytics router (mounted directly at /api for frontend compatibility)
app.include_router(analytics_router, prefix="/api")
