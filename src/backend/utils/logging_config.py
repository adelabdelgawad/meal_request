"""
Structured logging configuration with JSON output and correlation ID injection.

This module provides centralized logging configuration with:
1. JSON-formatted logs for better parsing
2. Correlation ID injection for request tracing
3. Context-aware logging
4. Log levels configurable via settings
"""

import asyncio
import logging
import logging.config
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import pytz

from core.config import settings

# Context variable for correlation ID (defined early for use in CorrelationIdFilter)
try:
    from contextvars import ContextVar

    correlation_id_var: ContextVar[Optional[str]] = ContextVar(
        "correlation_id", default=None
    )
except ImportError:
    # Fallback for Python < 3.7
    correlation_id_var = None


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""

    def __init__(self, correlation_id_header: str = "X-Correlation-ID"):
        super().__init__()
        self.correlation_id_header = correlation_id_header

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation ID to the log record."""
        # Try to get correlation ID from context var if available
        try:
            if correlation_id_var:
                correlation_id = correlation_id_var.get()
                if correlation_id:
                    record.correlation_id = correlation_id
                else:
                    record.correlation_id = "-"
            else:
                record.correlation_id = "-"
        except Exception:
            record.correlation_id = "-"

        return True


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Get color for this level
        color = self.COLORS.get(record.levelname, "")

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Build the log message
        level_str = f"{color}{record.levelname:8}{self.RESET}"
        logger_str = f"{self.DIM}{record.name}{self.RESET}"
        message = record.getMessage()

        # Format: timestamp | LEVEL | logger | message
        formatted = f"{self.DIM}{timestamp}{self.RESET} | {level_str} | {logger_str} | {message}"

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        import json

        # Base log fields
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=pytz.UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "exc_info",
                "exc_text",
                "stack_info",
                "getMessage",
                "correlation_id",
            }:
                # Convert complex objects to strings
                if isinstance(value, (dict, list, tuple)):
                    try:
                        log_data[key] = json.dumps(value, default=str)
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
                else:
                    log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
    log_level: Optional[str] = None,
    enable_json_logs: Optional[bool] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure structured logging.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json_logs: Whether to enable JSON formatting
        log_file: Optional log file path
    """
    # Get configuration from settings or use provided parameters
    log_level = log_level or settings.log_level
    enable_json_logs = (
        enable_json_logs if enable_json_logs is not None else settings.enable_json_logs
    )
    log_file = log_file or settings.log_file

    # Create log directory if needed
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    # Base logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
            },
            "standard": {
                "()": ColoredFormatter,
            },
        },
        "filters": {
            "correlation_id": {
                "()": CorrelationIdFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if enable_json_logs else "standard",
                "filters": ["correlation_id"],
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }

    # Add file handler if log file is specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json" if enable_json_logs else "standard",
            "filters": ["correlation_id"],
            "filename": log_file,
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf8",
        }

        # Add file handler to root logger
        config["loggers"][""]["handlers"].append("file")

    # Apply configuration
    logging.config.dictConfig(config)

    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "json_logs": enable_json_logs,
            "log_file": log_file,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID from context.

    Returns:
        Current correlation ID or None
    """
    if correlation_id_var:
        return correlation_id_var.get()
    return None


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID in context.

    Args:
        correlation_id: Correlation ID to set
    """
    if correlation_id_var:
        correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.

    Returns:
        New correlation ID (UUID4)
    """
    return str(uuid.uuid4())


# Decorator for automatic correlation ID
def log_execution(
    logger: Optional[logging.Logger] = None,
    include_args: bool = False,
    include_result: bool = False,
):
    """
    Decorator to add logging to function execution.

    Args:
        logger: Logger instance to use
        include_args: Whether to log function arguments
        include_result: Whether to log function result

    Returns:
        Decorated function
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            func_name = func.__name__
            correlation_id = generate_correlation_id()

            # Set correlation ID in context
            set_correlation_id(correlation_id)

            # Log function start
            log_data = {
                "function": func_name,
                "correlation_id": correlation_id,
            }
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)

            _logger.info(f"Starting {func_name}", extra=log_data)

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Log success
                log_data["status"] = "success"
                if include_result:
                    log_data["result"] = str(result)

                _logger.info(f"Completed {func_name}", extra=log_data)
                return result

            except Exception as e:
                # Log error
                log_data["status"] = "error"
                log_data["error"] = str(e)
                log_data["error_type"] = type(e).__name__

                _logger.error(f"Error in {func_name}", extra=log_data, exc_info=True)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            _logger = logger or get_logger(func.__module__)
            func_name = func.__name__
            correlation_id = generate_correlation_id()

            # Set correlation ID in context
            set_correlation_id(correlation_id)

            # Log function start
            log_data = {
                "function": func_name,
                "correlation_id": correlation_id,
            }
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)

            _logger.info(f"Starting {func_name}", extra=log_data)

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log success
                log_data["status"] = "success"
                if include_result:
                    log_data["result"] = str(result)

                _logger.info(f"Completed {func_name}", extra=log_data)
                return result

            except Exception as e:
                # Log error
                log_data["status"] = "error"
                log_data["error"] = str(e)
                log_data["error_type"] = type(e).__name__

                _logger.error(f"Error in {func_name}", extra=log_data, exc_info=True)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Export main functions
__all__ = [
    "setup_logging",
    "get_logger",
    "get_correlation_id",
    "set_correlation_id",
    "generate_correlation_id",
    "log_execution",
    "JSONFormatter",
    "ColoredFormatter",
    "CorrelationIdFilter",
]
