"""
Application settings using pydantic-settings for unified configuration management.
"""

import os
from typing import List, Optional, Union

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings as PydanticSettingsBase
from pydantic_settings import SettingsConfigDict

# Load .env file into os.environ for compatibility
load_dotenv()


class AppSettings(PydanticSettingsBase):
    """
    Application settings with environment variable support and vault integration.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environment and basic app settings
    ENVIRONMENT: str = "local"
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    LOG_LEVEL: str = "INFO"

    # CORS settings - parsed from indexed env vars or comma-separated string
    ALLOWED_ORIGINS: List[str] = Field(default_factory=list)

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """
        Parse ALLOWED_ORIGINS from various formats.

        Supports:
        - List (already parsed): ['http://localhost:3000']
        - Indexed env vars: ALLOWED_ORIGINS__0, ALLOWED_ORIGINS__1, etc.
        - Comma-separated string: 'http://localhost:3000,http://localhost:8080'
        - Empty/None: returns empty list
        """
        # Already a list - return as-is
        if isinstance(v, list):
            return [origin.strip() for origin in v if origin.strip()]

        # String format - split by comma
        if isinstance(v, str):
            if v.strip():
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            return []

        # Try indexed format (ALLOWED_ORIGINS__0, ALLOWED_ORIGINS__1, etc.)
        origins = []
        i = 0
        while True:
            env_var = f"ALLOWED_ORIGINS__{i}"
            value = os.getenv(env_var)
            if value is None:
                break
            origins.append(value.strip())
            i += 1

        if origins:
            return origins

        # Fallback to empty list
        return []

    # Database URLs (full DSNs)
    MARIA_URL: Optional[str] = None
    HRIS_URL: Optional[str] = None

    # LDAP / Active Directory settings
    AD_DOMAIN: Optional[str] = None
    AD_SERVER: Optional[str] = None
    SERVICE_ACCOUNT: Optional[str] = None
    SERVICE_PASSWORD: Optional[str] = None

    # AD Authentication Timeouts (seconds)
    AD_CONNECT_TIMEOUT: float = Field(
        default=3.0, description="AD LDAP connection timeout in seconds"
    )
    AD_READ_TIMEOUT: float = Field(
        default=3.0, description="AD LDAP read timeout in seconds"
    )
    AD_OVERALL_TIMEOUT: float = Field(
        default=5.0, description="Overall AD authentication timeout in seconds"
    )
    AD_MAX_CONCURRENT: int = Field(
        default=20, description="Maximum concurrent AD authentication requests"
    )

    # AD Circuit Breaker Settings
    AD_CIRCUIT_BREAKER_ENABLED: bool = Field(
        default=True, description="Enable circuit breaker for AD auth"
    )
    AD_CIRCUIT_BREAKER_THRESHOLD: int = Field(
        default=5, description="Failures before circuit breaker opens"
    )
    AD_CIRCUIT_BREAKER_TIMEOUT: float = Field(
        default=30.0, description="Seconds before attempting recovery"
    )

    # AD Organizational Units for user sync (comma-separated string)
    AD_ALLOWED_OUS: str = Field(
        default="",
        description="Comma-separated list of allowed OUs to fetch users from (e.g., CAR,SMH,ASH)",
    )
    AD_BASE_DN: str = Field(
        default="DC=andalusia,DC=loc", description="Base DN for AD searches"
    )
    AD_OU_PATH_TEMPLATE: str = Field(
        default="OU=Users,OU={ou},OU=Andalusia",
        description="OU path template. {ou} will be replaced with each allowed OU",
    )

    def get_ad_allowed_ous_list(self) -> List[str]:
        """Parse AD_ALLOWED_OUS string into a list."""
        if not self.AD_ALLOWED_OUS:
            return []
        # Strip whitespace, quotes, and brackets
        value = self.AD_ALLOWED_OUS.strip().strip("\"'").strip("[]")
        if not value:
            return []
        return [
            ou.strip().strip("\"'") for ou in value.split(",") if ou.strip()
        ]

    # Mail / EWS settings
    PRIMARY_SMTP_ADDRESS: Optional[str] = None
    SMTP_SERVER: Optional[str] = None
    CC_RECIPIENT: Optional[str] = None

    # Admin Account (for initial setup)
    APP_USERNAME: Optional[str] = None
    APP_PASSWORD: Optional[str] = None

    # Logging Configuration
    ENABLE_JSON_LOGS: bool = False
    LOG_FILE: Optional[str] = None

    # OpenTelemetry / Observability (optional)
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    OTEL_EXPORTER_OTLP_HEADERS: Optional[str] = None

    # Locale Configuration
    DEFAULT_LOCALE: str = Field(
        default="en", description="Default application locale (en or ar)"
    )
    SUPPORTED_LOCALES: List[str] = Field(
        default=["en", "ar"], description="List of supported locale codes"
    )
    LOCALE_COOKIE_NAME: str = Field(
        default="locale", description="Name of the locale preference cookie"
    )
    LOCALE_COOKIE_SECURE: bool = Field(
        default=False,
        description="Mark locale cookie as Secure (HTTPS only) - can be non-HttpOnly for JS access",
    )
    LOCALE_COOKIE_SAMESITE: str = Field(
        default="lax",
        description="SameSite attribute for locale cookie (strict, lax, none)",
    )
    LOCALE_COOKIE_MAX_AGE_DAYS: int = Field(
        default=365,
        description="Locale cookie lifetime in days (default: 1 year)",
    )

    # Stateful Sessions Configuration (ALWAYS ENABLED - Legacy mode removed)
    # USE_STATEFUL_SESSIONS removed - stateful sessions are now mandatory for security
    SESSION_COOKIE_NAME: str = Field(
        default="refresh", description="Name of the refresh token cookie"
    )
    SESSION_COOKIE_SECURE: bool = Field(
        default=True, description="Mark session cookie as Secure (HTTPS only)"
    )
    SESSION_COOKIE_SAMESITE: str = Field(
        default="strict",
        description="SameSite attribute for session cookie (strict, lax, none)",
    )
    SESSION_REFRESH_LIFETIME_DAYS: int = Field(
        default=30, description="Refresh token lifetime in days"
    )
    SESSION_ACCESS_TOKEN_MINUTES: int = Field(
        default=15, description="Access token lifetime in minutes"
    )
    SESSION_MAX_CONCURRENT: int = Field(
        default=5,
        description="Maximum concurrent active sessions per user (0 = unlimited)",
    )

    # Attendance Sync Configuration
    ATTENDANCE_SYNC_INTERVAL_MINUTES: int = Field(
        default=240,
        description="Attendance sync interval in minutes (default: 4 hours = 240 minutes)",
    )
    ATTENDANCE_SYNC_MONTHS_BACK: int = Field(
        default=2,
        description="Number of months to look back for attendance sync (default: 2)",
    )
    ATTENDANCE_SYNC_ENABLED: bool = Field(
        default=True,
        description="Enable automatic attendance sync background job",
    )
    ATTENDANCE_MIN_SHIFT_HOURS: float = Field(
        default=2.0,
        description="Minimum hours between in/out for valid shift completion. "
        "If out time is less than this after in time, employee is still on shift.",
    )

    # Celery / Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for Celery broker, result backend, and caching",
    )
    CELERY_ENABLED: bool = Field(
        default=True,
        description="Enable Celery for background task execution. When False, tasks run inline.",
    )
    CELERY_BROKER_URL: Optional[str] = Field(
        default=None,
        description="Celery broker URL (Redis recommended for production)",
    )
    CELERY_RESULT_BACKEND: Optional[str] = Field(
        default=None, description="Celery result backend"
    )

    # Redis Cache Configuration
    REDIS_ENABLED: bool = Field(
        default=True,
        description="Enable Redis for caching and rate limiting. When False, falls back to in-memory/database.",
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=20, description="Maximum connections in Redis connection pool"
    )
    REDIS_REVOKED_TOKEN_TTL_SECONDS: int = Field(
        default=900,  # 15 minutes (matches access token lifetime)
        description="TTL for revoked token cache entries in seconds",
    )
    REDIS_SESSION_CACHE_TTL_SECONDS: int = Field(
        default=300,  # 5 minutes
        description="TTL for session state cache entries in seconds",
    )
    REDIS_PERMISSION_CACHE_TTL_SECONDS: int = Field(
        default=600,  # 10 minutes
        description="TTL for user permission cache entries in seconds",
    )

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting on API endpoints"
    )
    RATE_LIMIT_LOGIN: str = Field(
        default="10/minute",
        description="Rate limit for login endpoint (brute force protection)",
    )
    RATE_LIMIT_DEFAULT: str = Field(
        default="100/minute",
        description="Default rate limit for API endpoints",
    )
    RATE_LIMIT_STRICT: str = Field(
        default="20/minute",
        description="Strict rate limit for sensitive endpoints",
    )

    def model_post_init(self, context):
        """
        Post-init hook to handle special configuration logic.

        - Loads secrets from vault when not in local mode
        - Handles MARIA_URL from APP_DB_URL
        - Handles Celery configuration
        """
        # Handle MARIA_URL from APP_DB_URL if not set
        if not self.MARIA_URL:
            app_db_url = os.getenv("APP_DB_URL")
            if app_db_url:
                self.MARIA_URL = app_db_url

        # Handle Celery configuration
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = os.getenv(
                "CELERY_BROKER_URL", self.REDIS_URL
            )

        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = os.getenv(
                "CELERY_RESULT_BACKEND", self.REDIS_URL
            )

        # Load secrets from vault when not in local mode
        if self.ENVIRONMENT != "local":
            from utils.secrets import get_secret

            # Load JWT secret from vault if not provided
            if not self.JWT_SECRET_KEY:
                try:
                    self.JWT_SECRET_KEY = get_secret("JWT_SECRET_KEY")
                except Exception:
                    # Don't fail if vault is not configured, just leave as None
                    pass


# Global settings instance
settings = AppSettings()
