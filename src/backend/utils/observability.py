"""
Observability utilities with Prometheus metrics and OpenTelemetry instrumentation.

This module provides:
1. Comprehensive Prometheus metrics for production monitoring:
   - HTTP request/response metrics (rate, latency, errors)
   - Business metrics (meal requests, user operations)
   - System metrics (CPU, memory, garbage collection)
   - Database metrics (queries, connections, transactions)
   - Celery task metrics (execution, failures, queue depth)
   - Redis cache metrics (hits, misses, connections)
2. OpenTelemetry SDK setup for distributed tracing
3. FastAPI instrumentation for automatic request tracing

Metrics are always enabled for production-grade monitoring.
"""

import gc
import logging
import os
import psutil
import time
from typing import Optional

from fastapi import FastAPI, Request, Response

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry (optional)
OPENTELEMETRY_AVAILABLE = False
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    trace = None
    pass

# Try to import Prometheus client (optional)
PROMETHEUS_AVAILABLE = False
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    from prometheus_client import GC_COLLECTOR, PLATFORM_COLLECTOR, PROCESS_COLLECTOR

    # Unregister default collectors to avoid conflicts with custom metrics
    # We'll create our own custom metrics with more control
    try:
        REGISTRY.unregister(GC_COLLECTOR)
        REGISTRY.unregister(PLATFORM_COLLECTOR)
        REGISTRY.unregister(PROCESS_COLLECTOR)
    except Exception:
        # Already unregistered or doesn't exist
        pass

    PROMETHEUS_AVAILABLE = True
except ImportError:
    REGISTRY = None
    pass


def _get_or_create_metric(metric_class, name: str, description: str, labelnames: list = None, **kwargs):
    """
    Get an existing metric or create a new one.

    This handles the case where the application is reloaded and metrics
    are already registered in the CollectorRegistry.
    """
    if not PROMETHEUS_AVAILABLE or REGISTRY is None:
        return None

    labelnames = labelnames or []

    # Check if metric already exists in registry
    for collector in list(REGISTRY._names_to_collectors.values()):
        if hasattr(collector, '_name') and collector._name == name:
            return collector

    # Create new metric
    try:
        if labelnames:
            return metric_class(name, description, labelnames, **kwargs)
        else:
            return metric_class(name, description, **kwargs)
    except ValueError as e:
        # Metric already registered (race condition or reload)
        if "Duplicated timeseries" in str(e):
            # Try to get the existing metric
            for collector in list(REGISTRY._names_to_collectors.values()):
                if hasattr(collector, '_name') and collector._name == name:
                    return collector
            # If we still can't find it, log and return None to avoid crashes
            logger.warning(f"Failed to create or retrieve metric '{name}': {e}")
            return None
        raise


# Configure OpenTelemetry
def setup_opentelemetry():
    """Setup OpenTelemetry tracing with OTLP exporter."""
    if not OPENTELEMETRY_AVAILABLE:
        return None

    # Create tracer provider
    trace.set_tracer_provider(TracerProvider())

    # Get the tracer
    tracer = trace.get_tracer(__name__)

    # Configure OTLP exporter (send to Jaeger/Zipkin/ Tempo)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        ),
        headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""),
    )

    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    return tracer


# Initialize tracer (may be None if OpenTelemetry not available)
tracer = setup_opentelemetry()

# Prometheus Metrics - Always available when prometheus_client is installed
# HTTP Metrics
REQUEST_COUNT = None
REQUEST_DURATION = None
REQUEST_SIZE = None
RESPONSE_SIZE = None
ACTIVE_REQUESTS = None

# Authentication & Security Metrics
AUTH_FAILURES = None
AUTH_SUCCESS = None
RATE_LIMIT_HITS = None

# Database Metrics
DB_QUERY_DURATION = None
DB_CONNECTION_POOL_SIZE = None
DB_TRANSACTION_DURATION = None

# Business Metrics - Meal Requests
MEAL_REQUESTS_TOTAL = None
MEAL_REQUESTS_BY_STATUS = None
MEAL_REQUEST_PROCESSING_DURATION = None

# User & Session Metrics
ACTIVE_USER_SESSIONS = None
USER_OPERATIONS_TOTAL = None

# Celery Task Metrics
CELERY_TASK_DURATION = None
CELERY_TASK_TOTAL = None
CELERY_QUEUE_LENGTH = None
CELERY_ACTIVE_TASKS = None

# System Metrics
PROCESS_CPU_USAGE = None
PROCESS_MEMORY_BYTES = None
PROCESS_THREADS = None
PYTHON_GC_COLLECTIONS = None
PYTHON_GC_DURATION = None

# Redis Cache Metrics
REDIS_CONNECTED_CLIENTS = None
REDIS_USED_MEMORY_BYTES = None
REDIS_KEYSPACE_HITS = None
REDIS_KEYSPACE_MISSES = None
REDIS_OPS_PER_SECOND = None

if PROMETHEUS_AVAILABLE:
    # HTTP Metrics
    REQUEST_COUNT = _get_or_create_metric(
        Counter,
        "http_requests_total",
        "Total number of HTTP requests",
        ["method", "endpoint", "status_code"],
    )

    REQUEST_DURATION = _get_or_create_metric(
        Histogram,
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    REQUEST_SIZE = _get_or_create_metric(
        Histogram,
        "http_request_size_bytes",
        "HTTP request size in bytes",
        ["method", "endpoint"],
        buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
    )

    RESPONSE_SIZE = _get_or_create_metric(
        Histogram,
        "http_response_size_bytes",
        "HTTP response size in bytes",
        ["method", "endpoint"],
        buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
    )

    ACTIVE_REQUESTS = _get_or_create_metric(
        Gauge,
        "http_requests_active",
        "Number of active HTTP requests being processed",
    )

    # Authentication & Security
    AUTH_FAILURES = _get_or_create_metric(
        Counter,
        "auth_failures_total",
        "Total number of authentication failures",
        ["reason"],
    )

    AUTH_SUCCESS = _get_or_create_metric(
        Counter,
        "auth_success_total",
        "Total number of successful authentications",
        ["method"],  # ldap, local
    )

    RATE_LIMIT_HITS = _get_or_create_metric(
        Counter,
        "rate_limit_hits_total",
        "Total number of rate limit hits",
        ["endpoint"],
    )

    # Database Metrics
    DB_QUERY_DURATION = _get_or_create_metric(
        Histogram,
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["operation", "table"],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    )

    DB_CONNECTION_POOL_SIZE = _get_or_create_metric(
        Gauge,
        "db_connection_pool_size",
        "Database connection pool size",
        ["pool", "state"],  # state: active, idle, total
    )

    DB_TRANSACTION_DURATION = _get_or_create_metric(
        Histogram,
        "db_transaction_duration_seconds",
        "Database transaction duration in seconds",
        ["operation"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    # Business Metrics - Meal Requests
    MEAL_REQUESTS_TOTAL = _get_or_create_metric(
        Counter,
        "meal_requests_total",
        "Total number of meal requests",
        ["status", "meal_type"],
    )

    MEAL_REQUESTS_BY_STATUS = _get_or_create_metric(
        Gauge,
        "meal_requests_by_status",
        "Current number of meal requests by status",
        ["status"],
    )

    MEAL_REQUEST_PROCESSING_DURATION = _get_or_create_metric(
        Histogram,
        "meal_request_processing_duration_seconds",
        "Time taken to process meal requests",
        ["operation"],  # create, approve, reject
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    )

    # User & Session Metrics
    ACTIVE_USER_SESSIONS = _get_or_create_metric(
        Gauge,
        "active_user_sessions",
        "Number of active user sessions",
        ["role"],
    )

    USER_OPERATIONS_TOTAL = _get_or_create_metric(
        Counter,
        "user_operations_total",
        "Total number of user operations",
        ["operation"],  # login, logout, create, update, delete
    )

    # Celery Task Metrics
    CELERY_TASK_DURATION = _get_or_create_metric(
        Histogram,
        "celery_task_duration_seconds",
        "Celery task execution duration",
        ["task_name", "status"],  # status: success, failure
        buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0],
    )

    CELERY_TASK_TOTAL = _get_or_create_metric(
        Counter,
        "celery_task_total",
        "Total number of Celery tasks executed",
        ["task_name", "status"],
    )

    CELERY_QUEUE_LENGTH = _get_or_create_metric(
        Gauge,
        "celery_queue_length",
        "Number of tasks waiting in Celery queue",
        ["queue_name"],
    )

    CELERY_ACTIVE_TASKS = _get_or_create_metric(
        Gauge,
        "celery_active_tasks",
        "Number of currently executing Celery tasks",
        ["worker"],
    )

    # System Metrics
    PROCESS_CPU_USAGE = _get_or_create_metric(
        Gauge,
        "process_cpu_usage_percent",
        "Process CPU usage percentage",
    )

    PROCESS_MEMORY_BYTES = _get_or_create_metric(
        Gauge,
        "process_memory_bytes",
        "Process memory usage in bytes",
        ["type"],  # rss, vms, shared
    )

    PROCESS_THREADS = _get_or_create_metric(
        Gauge,
        "process_threads",
        "Number of threads in the process",
    )

    PYTHON_GC_COLLECTIONS = _get_or_create_metric(
        Counter,
        "python_gc_collections_total",
        "Total Python garbage collections",
        ["generation"],
    )

    PYTHON_GC_DURATION = _get_or_create_metric(
        Histogram,
        "python_gc_duration_seconds",
        "Python garbage collection duration",
        ["generation"],
        buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    )

    # Redis Cache Metrics
    REDIS_CONNECTED_CLIENTS = _get_or_create_metric(
        Gauge,
        "redis_connected_clients",
        "Number of Redis connected clients",
    )

    REDIS_USED_MEMORY_BYTES = _get_or_create_metric(
        Gauge,
        "redis_used_memory_bytes",
        "Redis used memory in bytes",
    )

    REDIS_KEYSPACE_HITS = _get_or_create_metric(
        Counter,
        "redis_keyspace_hits_total",
        "Total Redis keyspace hits",
    )

    REDIS_KEYSPACE_MISSES = _get_or_create_metric(
        Counter,
        "redis_keyspace_misses_total",
        "Total Redis keyspace misses",
    )

    REDIS_OPS_PER_SECOND = _get_or_create_metric(
        Gauge,
        "redis_ops_per_second",
        "Redis operations per second",
    )


def record_request(request: Request, status_code: int, duration: float, request_size: int = 0, response_size: int = 0):
    """Record HTTP request metrics including size and duration."""
    if not PROMETHEUS_AVAILABLE or REQUEST_COUNT is None:
        return

    # Normalize endpoint to avoid high cardinality
    endpoint = _normalize_endpoint(request.url.path)

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=status_code,
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(duration)

    if REQUEST_SIZE and request_size > 0:
        REQUEST_SIZE.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(request_size)

    if RESPONSE_SIZE and response_size > 0:
        RESPONSE_SIZE.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(response_size)


def _normalize_endpoint(path: str) -> str:
    """Normalize endpoint paths to reduce cardinality."""
    # Replace UUIDs and numeric IDs with placeholders
    import re
    # UUID pattern
    path = re.sub(
        r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '/{id}',
        path,
        flags=re.IGNORECASE
    )
    # Numeric ID pattern
    path = re.sub(r'/\d+', '/{id}', path)
    return path


def record_auth_failure(reason: str):
    """Record authentication failure metrics."""
    if not PROMETHEUS_AVAILABLE or AUTH_FAILURES is None:
        return
    AUTH_FAILURES.labels(reason=reason).inc()


def record_auth_success(method: str):
    """Record successful authentication metrics."""
    if not PROMETHEUS_AVAILABLE or AUTH_SUCCESS is None:
        return
    AUTH_SUCCESS.labels(method=method).inc()


def record_rate_limit_hit(endpoint: str):
    """Record rate limit hit metrics."""
    if not PROMETHEUS_AVAILABLE or RATE_LIMIT_HITS is None:
        return
    RATE_LIMIT_HITS.labels(endpoint=endpoint).inc()


def update_db_connection_pool(pool_name: str, active: int, idle: int, total: int):
    """Update database connection pool metrics."""
    if not PROMETHEUS_AVAILABLE or DB_CONNECTION_POOL_SIZE is None:
        return
    DB_CONNECTION_POOL_SIZE.labels(pool=pool_name, state="active").set(active)
    DB_CONNECTION_POOL_SIZE.labels(pool=pool_name, state="idle").set(idle)
    DB_CONNECTION_POOL_SIZE.labels(pool=pool_name, state="total").set(total)


def record_db_query(operation: str, table: str, duration: float):
    """Record database query metrics."""
    if not PROMETHEUS_AVAILABLE or DB_QUERY_DURATION is None:
        return
    DB_QUERY_DURATION.labels(operation=operation, table=table).observe(duration)


def record_db_transaction(operation: str, duration: float):
    """Record database transaction metrics."""
    if not PROMETHEUS_AVAILABLE or DB_TRANSACTION_DURATION is None:
        return
    DB_TRANSACTION_DURATION.labels(operation=operation).observe(duration)


# Business Metrics Functions
def record_meal_request(status: str, meal_type: str):
    """Record meal request creation/update."""
    if not PROMETHEUS_AVAILABLE or MEAL_REQUESTS_TOTAL is None:
        return
    MEAL_REQUESTS_TOTAL.labels(status=status, meal_type=meal_type).inc()


def update_meal_requests_by_status(status: str, count: int):
    """Update current count of meal requests by status."""
    if not PROMETHEUS_AVAILABLE or MEAL_REQUESTS_BY_STATUS is None:
        return
    MEAL_REQUESTS_BY_STATUS.labels(status=status).set(count)


def record_meal_request_processing(operation: str, duration: float):
    """Record meal request processing time."""
    if not PROMETHEUS_AVAILABLE or MEAL_REQUEST_PROCESSING_DURATION is None:
        return
    MEAL_REQUEST_PROCESSING_DURATION.labels(operation=operation).observe(duration)


# User & Session Metrics Functions
def update_active_sessions(role: str, count: int):
    """Update active user sessions count."""
    if not PROMETHEUS_AVAILABLE or ACTIVE_USER_SESSIONS is None:
        return
    ACTIVE_USER_SESSIONS.labels(role=role).set(count)


def record_user_operation(operation: str):
    """Record user operation (login, logout, create, update, delete)."""
    if not PROMETHEUS_AVAILABLE or USER_OPERATIONS_TOTAL is None:
        return
    USER_OPERATIONS_TOTAL.labels(operation=operation).inc()


# Celery Metrics Functions
def record_celery_task(task_name: str, status: str, duration: float):
    """Record Celery task execution."""
    if not PROMETHEUS_AVAILABLE or CELERY_TASK_DURATION is None:
        return
    CELERY_TASK_DURATION.labels(task_name=task_name, status=status).observe(duration)
    CELERY_TASK_TOTAL.labels(task_name=task_name, status=status).inc()


def update_celery_queue_length(queue_name: str, length: int):
    """Update Celery queue length."""
    if not PROMETHEUS_AVAILABLE or CELERY_QUEUE_LENGTH is None:
        return
    CELERY_QUEUE_LENGTH.labels(queue_name=queue_name).set(length)


def update_celery_active_tasks(worker: str, count: int):
    """Update number of active Celery tasks."""
    if not PROMETHEUS_AVAILABLE or CELERY_ACTIVE_TASKS is None:
        return
    CELERY_ACTIVE_TASKS.labels(worker=worker).set(count)


# System Metrics Collection
def collect_system_metrics():
    """Collect system metrics (CPU, memory, threads, GC stats)."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        # Get process object
        process = psutil.Process()

        # CPU usage
        if PROCESS_CPU_USAGE:
            cpu_percent = process.cpu_percent(interval=0.1)
            PROCESS_CPU_USAGE.set(cpu_percent)

        # Memory usage
        if PROCESS_MEMORY_BYTES:
            memory_info = process.memory_info()
            PROCESS_MEMORY_BYTES.labels(type="rss").set(memory_info.rss)
            PROCESS_MEMORY_BYTES.labels(type="vms").set(memory_info.vms)
            if hasattr(memory_info, 'shared'):
                PROCESS_MEMORY_BYTES.labels(type="shared").set(memory_info.shared)

        # Thread count
        if PROCESS_THREADS:
            PROCESS_THREADS.set(process.num_threads())

        # Garbage collection stats
        if PYTHON_GC_COLLECTIONS:
            gc_stats = gc.get_stats()
            for gen in range(3):  # Python has 3 generations
                if gen < len(gc_stats):
                    collections = gc_stats[gen].get('collections', 0)
                    PYTHON_GC_COLLECTIONS.labels(generation=str(gen)).inc(collections)

    except Exception as e:
        logger.warning(f"Failed to collect system metrics: {e}")


# Redis Metrics Collection
async def collect_redis_metrics():
    """Collect Redis cache metrics."""
    if not PROMETHEUS_AVAILABLE:
        return

    try:
        from core.redis import is_redis_available, get_redis

        if not is_redis_available():
            return

        redis_client = get_redis()
        if not redis_client:
            return

        # Get Redis INFO
        info = await redis_client.info()

        # Connected clients
        if REDIS_CONNECTED_CLIENTS:
            REDIS_CONNECTED_CLIENTS.set(info.get('connected_clients', 0))

        # Memory usage
        if REDIS_USED_MEMORY_BYTES:
            REDIS_USED_MEMORY_BYTES.set(info.get('used_memory', 0))

        # Keyspace stats
        if REDIS_KEYSPACE_HITS and REDIS_KEYSPACE_MISSES:
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            # These are cumulative, so we just set them
            # The rate() function in Prometheus will calculate the rate
            REDIS_KEYSPACE_HITS.inc(hits)
            REDIS_KEYSPACE_MISSES.inc(misses)

        # Operations per second
        if REDIS_OPS_PER_SECOND:
            ops = info.get('instantaneous_ops_per_sec', 0)
            REDIS_OPS_PER_SECOND.set(ops)

    except Exception as e:
        logger.warning(f"Failed to collect Redis metrics: {e}")


# Database query monitoring decorator
def monitor_db_query(operation: str, table: str):
    """Decorator to monitor database query duration."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                record_db_query(operation, table, duration)
                return result
            except Exception:
                duration = time.time() - start_time
                record_db_query(operation, table, duration)
                raise

        return wrapper

    return decorator


# Custom middleware for request timing and metrics
async def observability_middleware(request: Request, call_next):
    """FastAPI middleware for request timing, tracing, and comprehensive metrics."""
    start_time = time.time()

    # Add request ID for tracing
    request_id = os.urandom(8).hex()
    request.state.request_id = request_id

    # Track active requests
    if ACTIVE_REQUESTS:
        ACTIVE_REQUESTS.inc()

    # Get request size
    request_size = 0
    if request.headers.get("content-length"):
        try:
            request_size = int(request.headers.get("content-length"))
        except ValueError:
            pass

    response = await call_next(request)

    # Track active requests
    if ACTIVE_REQUESTS:
        ACTIVE_REQUESTS.dec()

    # Calculate duration
    duration = time.time() - start_time

    # Get response size
    response_size = 0
    if hasattr(response, "headers") and response.headers.get("content-length"):
        try:
            response_size = int(response.headers.get("content-length"))
        except ValueError:
            pass

    # Record comprehensive metrics
    record_request(
        request,
        response.status_code,
        duration,
        request_size=request_size,
        response_size=response_size
    )

    # Add response headers
    response.headers["X-Request-ID"] = request_id

    return response


# Health endpoint
def setup_health_endpoint(app: FastAPI):
    """Setup the /health endpoint for health checks."""

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "meal_request_api",
        }

    return app


# Metrics endpoint
def setup_metrics_endpoint(app: FastAPI):
    """Setup the /metrics endpoint for Prometheus scraping with comprehensive metrics."""
    if not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus client not available - metrics endpoint disabled")
        return app

    @app.get("/metrics")
    async def metrics():
        """
        Expose Prometheus metrics in standard format.

        This endpoint provides:
        - HTTP request/response metrics
        - Business metrics (meal requests, user operations)
        - System metrics (CPU, memory, GC)
        - Database metrics (queries, connections)
        - Celery task metrics
        - Redis cache metrics
        """
        # Collect latest system metrics before returning
        collect_system_metrics()

        # Collect Redis metrics
        try:
            await collect_redis_metrics()
        except Exception as e:
            logger.warning(f"Failed to collect Redis metrics: {e}")

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    logger.info("Prometheus metrics endpoint configured at /metrics")
    return app


# FastAPI instrumentation
def instrument_fastapi(app: FastAPI):
    """Instrument FastAPI with OpenTelemetry."""
    if not OPENTELEMETRY_AVAILABLE:
        return app
    try:
        FastAPIInstrumentor.instrument_app(app)
        return app
    except Exception as e:
        # Fallback if instrumentation fails
        logger.warning(f"FastAPI instrumentation failed: {e}")
        return app


# Database instrumentation
def instrument_database():
    """Instrument SQLAlchemy with OpenTelemetry."""
    if not OPENTELEMETRY_AVAILABLE:
        return
    try:
        SQLAlchemyInstrumentor().instrument()
    except Exception as e:
        # Fallback if instrumentation fails
        logger.warning(f"SQLAlchemy instrumentation failed: {e}")


# Initialize instrumentation
def init_observability(app: Optional[FastAPI] = None):
    """Initialize all observability components."""
    try:
        # Instrument database
        instrument_database()

        # Instrument FastAPI if app provided
        if app:
            instrument_fastapi(app)
            setup_metrics_endpoint(app)
            setup_health_endpoint(app)

            # Add middleware
            app.middleware("http")(observability_middleware)

        return True
    except Exception as e:
        logger.warning(f"Observability initialization failed: {e}")
        return False


# Export main functions
__all__ = [
    # HTTP Metrics
    "record_request",
    # Authentication Metrics
    "record_auth_failure",
    "record_auth_success",
    "record_rate_limit_hit",
    # Database Metrics
    "update_db_connection_pool",
    "record_db_query",
    "record_db_transaction",
    "monitor_db_query",
    # Business Metrics
    "record_meal_request",
    "update_meal_requests_by_status",
    "record_meal_request_processing",
    # User & Session Metrics
    "update_active_sessions",
    "record_user_operation",
    # Celery Metrics
    "record_celery_task",
    "update_celery_queue_length",
    "update_celery_active_tasks",
    # System Metrics
    "collect_system_metrics",
    "collect_redis_metrics",
    # Setup Functions
    "init_observability",
    "setup_metrics_endpoint",
    # Tracing
    "tracer",
    # Availability Flags
    "OPENTELEMETRY_AVAILABLE",
    "PROMETHEUS_AVAILABLE",
]
