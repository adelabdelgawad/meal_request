"""
Core domain layer - shared infrastructure for the application.

Includes:
- Domain exceptions
- Security utilities (password hashing, JWT)
- Database session management
- Pagination helpers
- Redis connection management
"""

from core.exceptions import (
    ConflictError,
    DomainException,
    NotFoundError,
    ValidationError,
)
from core.redis import (
    RedisKeys,
    acquire_lock,
    cache_delete,
    cache_exists,
    cache_get,
    cache_set,
    close_redis,
    extend_lock,
    get_redis,
    get_redis_or_fail,
    init_redis,
    is_redis_available,
    redis_health_check,
    release_lock,
)
from core.security import create_jwt, decode_jwt, hash_password, verify_password

__all__ = [
    # Exceptions
    "DomainException",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    # Security
    "hash_password",
    "verify_password",
    "create_jwt",
    "decode_jwt",
    # Redis
    "init_redis",
    "close_redis",
    "get_redis",
    "get_redis_or_fail",
    "is_redis_available",
    "redis_health_check",
    "RedisKeys",
    "cache_set",
    "cache_get",
    "cache_delete",
    "cache_exists",
    "acquire_lock",
    "release_lock",
    "extend_lock",
]
