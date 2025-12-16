# ==============================================================================
# Production-Ready Dockerfile for FastAPI Backend
# Base: Python 3.12 Alpine with UV Package Manager
# Optimized for minimal size and maximum security
# ==============================================================================

# ==============================================================================
# STAGE 1: Builder - Compile dependencies and build application
# ==============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

# Set working directory
WORKDIR /app

# Enable bytecode compilation for faster startup and smaller size
# UV_LINK_MODE=copy ensures proper file copying instead of hardlinks
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install build dependencies for Alpine
# These are required to compile Python packages with C extensions
RUN apk add --no-cache \
    # Core build tools
    gcc \
    musl-dev \
    g++ \
    make \
    # SSL/TLS support (cryptography, requests)
    libffi-dev \
    openssl-dev \
    # LDAP support (ldap3)
    openldap-dev \
    cyrus-sasl-dev \
    # MySQL/MariaDB support (aiomysql, pymysql)
    mariadb-dev \
    mariadb-connector-c \
    # ODBC support (pyodbc for SQL Server)
    unixodbc-dev \
    freetds-dev \
    # XML parsing (lxml, exchangelib)
    libxml2-dev \
    libxslt-dev \
    # PostgreSQL (if needed in future)
    postgresql-dev \
    # For packages requiring Rust (cryptography >= 3.4)
    rust \
    cargo \
    # Additional utilities
    linux-headers \
    pkgconfig

# Copy dependency files first (for better caching)
# Only rebuilds if these files change
COPY pyproject.toml uv.lock ./

# Install dependencies using uv with cache mount
# --locked: Use exact versions from uv.lock (reproducible builds)
# --no-install-project: Don't install the project itself yet
# --no-editable: Install as regular packages (not editable/development mode)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

# Copy application source code
COPY . .

# Install the project with all dependencies
# This creates a complete, non-editable installation
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# ==============================================================================
# STAGE 2: Runtime - Minimal production image
# ==============================================================================
FROM python:3.12-alpine AS runtime

# Production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install ONLY runtime dependencies (no build tools)
# Keep image size minimal and attack surface small
RUN apk add --no-cache \
    # HTTP client for health checks
    curl \
    wget \
    # CA certificates for HTTPS
    ca-certificates \
    # Runtime libraries (matching build dependencies)
    libffi \
    openssl \
    libldap \
    libsasl \
    mariadb-connector-c \
    unixodbc \
    freetds \
    libxml2 \
    libxslt \
    libpq \
    # Timezone data
    tzdata \
    && update-ca-certificates

# Create non-root user for security
# UID 1000 is standard for application users
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder stage
# This contains all installed packages and bytecode
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# Copy application code with proper ownership
COPY --from=builder --chown=appuser:appuser /app /app

# Create directories for logs and data with proper permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app/logs /app/data && \
    chmod 755 /app/logs /app/data

# Add .venv/bin to PATH for direct command access
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user (security best practice)
USER appuser

# Health check for container orchestration
# Checks if the app is responding on /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# Expose application port
EXPOSE 8000

# Production command using Gunicorn with Uvicorn workers
# Workers: 4 (adjust based on CPU cores in deployment)
# Worker class: UvicornWorker for ASGI support
# Timeout: 300s for long-running requests
# Bind: 0.0.0.0:8000 for container networking
# Logs: stdout/stderr for container log aggregation
CMD ["gunicorn", "app:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--graceful-timeout", "30"]

# Alternative CMD for simpler deployments (uncomment if preferred):
# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Metadata labels
LABEL maintainer="meal-request-team" \
      version="2.0.0" \
      description="Meal Request Backend - Production Alpine Build" \
      python.version="3.12" \
      base.image="python:3.14-alpine"
