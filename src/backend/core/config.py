"""
Application settings using hierarchical pydantic-settings.
"""

import os
from typing import List

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """API configuration settings."""

    title: str = "Employee Meal Request API"
    description: str = "API for managing employee meal requests"
    version: str = "1.0.0"
    cors_origins: List[str] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, list):
            return [origin.strip() for origin in v if origin.strip()]
        if isinstance(v, str):
            if v.strip():
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            return []
        return []

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field(default="")
    hris_url: str = Field(default="")
    biostar_url: str = Field(default="")

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class SecretSettings(BaseSettings):
    """Security configuration settings."""

    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    model_config = SettingsConfigDict(
        env_prefix="SECRET_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    url: str = Field(default="redis://localhost:6379/0")
    max_connections: int = 20
    enabled: bool = True
    revoked_token_ttl_seconds: int = 900
    session_cache_ttl_seconds: int = 300
    permission_cache_ttl_seconds: int = 600

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class LDAPSettings(BaseSettings):
    """LDAP/Active Directory configuration settings."""

    domain: str = ""
    server: str = ""
    service_account: str = ""
    service_password: str = ""

    connect_timeout: float = 3.0
    read_timeout: float = 3.0
    overall_timeout: float = 5.0
    max_concurrent: int = 20

    circuit_breaker_enabled: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0

    allowed_ous: str = ""
    base_dn: str = "DC=andalusia,DC=loc"
    ou_path_template: str = "OU=Users,OU={ou},OU=Andalusia"

    def get_allowed_ous_list(self) -> List[str]:
        """Parse AD_ALLOWED_OUS string into a list."""
        if not self.allowed_ous:
            return []
        value = self.allowed_ous.strip().strip("\"'").strip("[]")
        if not value:
            return []
        return [ou.strip().strip("\"'") for ou in value.split(",") if ou.strip()]

    model_config = SettingsConfigDict(
        env_prefix="AD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class CelerySettings(BaseSettings):
    """Celery configuration settings."""

    enabled: bool = True
    broker_url: str = ""
    result_backend: str = ""

    model_config = SettingsConfigDict(
        env_prefix="CELERY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class EmailSettings(BaseSettings):
    """Email/SMTP configuration settings."""

    primary_smtp_address: str = ""
    smtp_server: str = ""
    cc_recipient: str = ""

    model_config = SettingsConfigDict(
        env_prefix="SMTP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class LocaleSettings(BaseSettings):
    """Locale configuration settings."""

    default_locale: str = "en"
    supported_locales: List[str] = ["en", "ar"]
    cookie_name: str = "locale"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_max_age_days: int = 365

    model_config = SettingsConfigDict(
        env_prefix="LOCALE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class SessionSettings(BaseSettings):
    """Stateful session configuration settings."""

    cookie_name: str = "refresh"
    cookie_secure: bool = True
    cookie_samesite: str = "strict"
    refresh_lifetime_days: int = 30
    access_token_minutes: int = 15
    max_concurrent: int = 5

    model_config = SettingsConfigDict(
        env_prefix="SESSION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class AttendanceSettings(BaseSettings):
    """Attendance sync configuration settings."""

    sync_interval_minutes: int = 240
    sync_months_back: int = 2
    enabled: bool = True
    min_shift_hours: float = 2.0

    model_config = SettingsConfigDict(
        env_prefix="ATTENDANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration settings."""

    enabled: bool = True
    login: str = "10/minute"
    default: str = "100/minute"
    strict: str = "20/minute"

    model_config = SettingsConfigDict(
        env_prefix="RATE_LIMIT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main application settings."""

    environment: str = "local"
    log_level: str = "INFO"
    enable_json_logs: bool = False
    log_file: str = ""

    api: APISettings = APISettings()
    database: DatabaseSettings = DatabaseSettings()
    sec: SecretSettings = SecretSettings()
    redis: RedisSettings = RedisSettings()
    ldap: LDAPSettings = LDAPSettings()
    celery: CelerySettings = CelerySettings()
    email: EmailSettings = EmailSettings()
    locale: LocaleSettings = LocaleSettings()
    session: SessionSettings = SessionSettings()
    attendance: AttendanceSettings = AttendanceSettings()
    rate_limit: RateLimitSettings = RateLimitSettings()

    admin_username: str = ""
    admin_password: str = ""

    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def model_post_init(self, context):
        """Post-init hook for special configuration logic."""
        # Handle legacy environment variables for migration
        if not self.database.url:
            url = os.getenv("MARIA_URL") or os.getenv("APP_DB_URL")
            if url:
                self.database.url = url

        if not self.database.hris_url:
            hris_url = os.getenv("HRIS_URL")
            if hris_url:
                self.database.hris_url = hris_url

        # Handle Celery fallback
        if not self.celery.broker_url:
            self.celery.broker_url = self.redis.url
        if not self.celery.result_backend:
            self.celery.result_backend = self.redis.url

        # Handle legacy ALLOWED_ORIGINS
        if not self.api.cors_origins:
            allowed_origins = os.getenv("ALLOWED_ORIGINS")
            if allowed_origins:
                self.api.cors_origins = APISettings.parse_cors_origins(
                    allowed_origins
                )

        # Handle legacy JWT_SECRET_KEY
        if not self.sec.jwt_secret_key:
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            if jwt_secret:
                self.sec.jwt_secret_key = jwt_secret

        # Handle legacy admin credentials
        if not self.admin_username:
            self.admin_username = os.getenv("APP_USERNAME", "")
        if not self.admin_password:
            self.admin_password = os.getenv("APP_PASSWORD", "")

        # Load secrets from vault when not in local mode
        if self.environment != "local":
            try:
                from utils.secrets import get_secret

                if not self.sec.jwt_secret_key:
                    secret = get_secret("JWT_SECRET_KEY")
                    if secret:
                        self.sec.jwt_secret_key = secret
            except Exception:
                pass


# Global settings instance
settings = Settings()
