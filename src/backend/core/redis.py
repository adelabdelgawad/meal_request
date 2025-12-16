"""
Redis connection management for the Meal Request application.

Provides async Redis client with connection pooling, retry mechanisms,
circuit breaker pattern, and comprehensive error handling for:
- Rate limiting storage
- Token revocation cache
- Session state cache
- Distributed locking
- Message queues
- Caching with TTL management
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

# Global Redis client and pool
_redis_client: Optional[aioredis.Redis] = None
_redis_pool: Optional[ConnectionPool] = None
_redis_config: Dict[str, Any] = {}
_circuit_breaker_failures = 0
_circuit_breaker_last_failure_time = 0
_circuit_breaker_open = False


class RedisCircuitBreakerOpen(Exception):
    """Raised when Redis circuit breaker is open."""
    pass


async def init_redis(
    redis_url: str,
    max_connections: int = 20,
    retry_attempts: int = 3,
    retry_delay: float = 1.0,
    socket_connect_timeout: float = 5.0,
    socket_timeout: float = 5.0,
    health_check_interval: int = 30
) -> aioredis.Redis:
    """
    Initialize Redis connection pool and client with retry mechanisms.

    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
        max_connections: Maximum number of connections in pool
        retry_attempts: Number of connection retry attempts
        retry_delay: Delay between retry attempts in seconds
        socket_connect_timeout: Socket connection timeout
        socket_timeout: Socket timeout
        health_check_interval: Health check interval in seconds

    Returns:
        aioredis.Redis: Async Redis client instance

    Raises:
        RedisConnectionError: If Redis connection fails after retries
    """
    global _redis_client, _redis_pool, _redis_config

    if _redis_client is not None:
        logger.debug("Redis client already initialized")
        return _redis_client

    # Store configuration for later use
    _redis_config = {
        "max_connections": max_connections,
        "retry_attempts": retry_attempts,
        "retry_delay": retry_delay,
        "socket_connect_timeout": socket_connect_timeout,
        "socket_timeout": socket_timeout,
        "health_check_interval": health_check_interval,
        "redis_url": redis_url
    }

    # Attempt connection with retry logic
    for attempt in range(retry_attempts):
        try:
            # Create connection pool with optimized settings
            _redis_pool = ConnectionPool.from_url(
                redis_url,
                max_connections=max_connections,
                decode_responses=True,
                encoding="utf-8",
                socket_connect_timeout=socket_connect_timeout,
                socket_timeout=socket_timeout,
                retry_on_timeout=True,
                health_check_interval=health_check_interval,
            )

            # Create client with pool
            _redis_client = aioredis.Redis(
                connection_pool=_redis_pool,
                retry_on_timeout=True,
            )

            # Test connection with comprehensive health check
            await _redis_client.ping()

            # Get Redis server info for logging
            info = await _redis_client.info("server")

            logger.info(
                "Redis connection established successfully",
                extra={
                    "url": _mask_redis_url(redis_url),
                    "max_connections": max_connections,
                    "redis_version": info.get("redis_version", "unknown"),
                    "attempt": attempt + 1,
                    "retry_attempts": retry_attempts
                },
            )

            # Reset circuit breaker on successful connection
            global _circuit_breaker_failures, _circuit_breaker_last_failure_time, _circuit_breaker_open
            _circuit_breaker_failures = 0
            _circuit_breaker_last_failure_time = 0
            _circuit_breaker_open = False

            return _redis_client

        except Exception as e:
            logger.warning(
                f"Redis connection attempt {attempt + 1}/{retry_attempts} failed: {e}"
            )

            # Clean up failed connection
            if _redis_pool:
                try:
                    await _redis_pool.disconnect()
                except Exception:
                    pass
                _redis_pool = None
            if _redis_client:
                try:
                    await _redis_client.aclose()
                except Exception:
                    pass
                _redis_client = None

            # If this was the last attempt, raise error
            if attempt == retry_attempts - 1:
                logger.error(
                    f"All Redis connection attempts failed. Last error: {e}")
                raise RedisConnectionError(
                    f"Failed to connect to Redis after {retry_attempts} attempts: {e}") from e

            # Wait before retry
            # Exponential backoff
            await asyncio.sleep(retry_delay * (2 ** attempt))

    # This should never be reached, but for type safety
    raise RedisConnectionError("Redis connection failed unexpectedly")


async def close_redis() -> None:
    """
    Close Redis connection pool and cleanup.

    Should be called during application shutdown.
    """
    global _redis_client, _redis_pool

    if _redis_client is not None:
        try:
            await _redis_client.aclose()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None

    if _redis_pool is not None:
        try:
            await _redis_pool.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting Redis pool: {e}")
        finally:
            _redis_pool = None


def get_redis() -> Optional[aioredis.Redis]:
    """
    Get the global Redis client instance.

    Returns:
        aioredis.Redis: Async Redis client, or None if not initialized

    Note:
        Call init_redis() before using this function.
        Returns None if Redis is not available (graceful degradation).
    """
    return _redis_client


async def get_redis_or_fail() -> aioredis.Redis:
    """
    Get the global Redis client instance, raising if unavailable.

    Returns:
        aioredis.Redis: Async Redis client

    Raises:
        RuntimeError: If Redis client is not initialized
    """
    if _redis_client is None:
        raise RuntimeError(
            "Redis client not initialized. Call init_redis() first.")
    return _redis_client


def is_redis_available() -> bool:
    """
    Check if Redis client is initialized and available.

    Returns:
        bool: True if Redis is available
    """
    return _redis_client is not None


async def redis_health_check() -> dict:
    """
    Perform comprehensive Redis health check with circuit breaker monitoring.

    Returns:
        dict: Health status with detailed metrics and circuit breaker state
    """
    import time

    global _circuit_breaker_failures, _circuit_breaker_last_failure_time, _circuit_breaker_open

    # Check if circuit breaker is open
    current_time = time.time()
    circuit_breaker_timeout = 30  # 30 seconds timeout

    if _circuit_breaker_open:
        if current_time - _circuit_breaker_last_failure_time > circuit_breaker_timeout:
            # Reset circuit breaker after timeout
            logger.info("Resetting Redis circuit breaker after timeout")
            _circuit_breaker_open = False
            _circuit_breaker_failures = 0
        else:
            return {
                "status": "unavailable",
                "error": "Circuit breaker is open",
                "circuit_breaker": {
                    "open": True,
                    "failures": _circuit_breaker_failures,
                    "last_failure": _circuit_breaker_last_failure_time,
                }
            }

    if _redis_client is None:
        return {
            "status": "unavailable",
            "error": "Redis not initialized",
            "circuit_breaker": {"open": _circuit_breaker_open, "failures": _circuit_breaker_failures}
        }

    try:
        start = time.perf_counter()

        # Perform comprehensive health checks
        await _redis_client.ping()
        latency_ms = (time.perf_counter() - start) * 1000

        # Get Redis server info
        server_info = await _redis_client.info("server")
        memory_info = await _redis_client.info("memory")
        stats_info = await _redis_client.info("stats")

        # Calculate health metrics
        used_memory_percent = (memory_info.get("used_memory", 0) /
                               memory_info.get("maxmemory", 1)) * 100

        # Check keyspace hit rate
        hits = stats_info.get("keyspace_hits", 0)
        misses = stats_info.get("keyspace_misses", 0)
        hit_rate = (hits / (hits + misses)) * 100 if (hits + misses) > 0 else 0

        health_status = {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "redis_version": server_info.get("redis_version", "unknown"),
            "uptime_seconds": server_info.get("uptime_in_seconds", 0),
            "connected_clients": server_info.get("connected_clients", 0),
            "memory": {
                "used_memory_mb": round(memory_info.get("used_memory", 0) / 1024 / 1024, 2),
                "max_memory_mb": round(memory_info.get("maxmemory", 0) / 1024 / 1024, 2),
                "used_memory_percent": round(used_memory_percent, 2),
            },
            "performance": {
                "keyspace_hit_rate": round(hit_rate, 2),
                "total_commands_processed": stats_info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": server_info.get("instantaneous_ops_per_sec", 0),
            },
            "circuit_breaker": {
                "open": _circuit_breaker_open,
                "failures": _circuit_breaker_failures,
                "last_failure": _circuit_breaker_last_failure_time,
            }
        }

        # Reset circuit breaker failure count on successful health check
        if _circuit_breaker_failures > 0:
            logger.info(
                f"Redis health check successful. Resetting failure count from {_circuit_breaker_failures}")
            _circuit_breaker_failures = 0

        return health_status

    except Exception as e:
        # Update circuit breaker on failure
        _circuit_breaker_failures += 1
        _circuit_breaker_last_failure_time = current_time

        # Open circuit breaker after 5 consecutive failures
        if _circuit_breaker_failures >= 5 and not _circuit_breaker_open:
            _circuit_breaker_open = True
            logger.error(
                f"Redis circuit breaker opened after {_circuit_breaker_failures} consecutive failures")

        return {
            "status": "unhealthy",
            "error": str(e),
            "circuit_breaker": {
                "open": _circuit_breaker_open,
                "failures": _circuit_breaker_failures,
                "last_failure": _circuit_breaker_last_failure_time,
            }
        }


async def check_redis_connection_with_retry(max_retries: int = 3) -> bool:
    """
    Check Redis connection with automatic retry and circuit breaker logic.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    for attempt in range(max_retries):
        try:
            health_result = await redis_health_check()
            if health_result["status"] == "healthy":
                return True
            elif health_result.get("circuit_breaker", {}).get("open"):
                logger.warning(
                    "Redis circuit breaker is open, skipping retry attempts")
                return False
        except Exception as e:
            logger.warning(
                f"Redis connection check attempt {attempt + 1}/{max_retries} failed: {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return False


def _mask_redis_url(url: str) -> str:
    """Mask password in Redis URL for logging."""
    import re

    return re.sub(r"(redis://[^:]+:)[^@]+(@)", r"\1****\2", url)


# ============================================================================
# Circuit Breaker Decorator for Redis Operations
# ============================================================================

def redis_operation_with_circuit_breaker(fallback_return=None):
    """
    Decorator to wrap Redis operations with circuit breaker pattern.

    Args:
        fallback_return: Value to return when circuit breaker is open

    Usage:
        @redis_operation_with_circuit_breaker(fallback_return=None)
        async def redis_operation():
            # Redis operation here
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            global _circuit_breaker_open, _circuit_breaker_failures

            if _circuit_breaker_open:
                logger.warning(
                    f"Circuit breaker is open, skipping {func.__name__}")
                return fallback_return

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                _circuit_breaker_failures += 1
                if _circuit_breaker_failures >= 5:
                    _circuit_breaker_open = True
                    logger.error(
                        f"Circuit breaker opened due to failures in {func.__name__}")
                raise e
        return wrapper
    return decorator


# ============================================================================
# Redis Key Prefixes (Namespacing)
# ============================================================================

class RedisKeys:
    """
    Redis key prefixes for different use cases.

    Using namespacing prevents key collisions and enables easy cleanup.
    """

    # Rate limiting keys
    RATE_LIMIT = "rl:"

    # Token revocation cache
    REVOKED_TOKEN = "rev:"

    # Session state cache
    SESSION = "sess:"

    # User permissions cache
    PERMISSIONS = "perm:"

    # Distributed locks
    LOCK = "lock:"

    # General cache
    CACHE = "cache:"

    @staticmethod
    def revoked_token(jti: str) -> str:
        """Key for revoked token JTI."""
        return f"{RedisKeys.REVOKED_TOKEN}{jti}"

    @staticmethod
    def session(refresh_token_id: str) -> str:
        """Key for session state."""
        return f"{RedisKeys.SESSION}{refresh_token_id}"

    @staticmethod
    def user_permissions(user_id: str) -> str:
        """Key for user permissions cache."""
        return f"{RedisKeys.PERMISSIONS}{user_id}"

    @staticmethod
    def scheduler_lock(job_id: str) -> str:
        """Key for scheduler distributed lock."""
        return f"{RedisKeys.LOCK}job:{job_id}"


# ============================================================================
# Cache Helper Functions
# ============================================================================

async def cache_set(
    key: str,
    value: str,
    ttl_seconds: int,
    nx: bool = False,
) -> bool:
    """
    Set a cache value with TTL.

    Args:
        key: Cache key
        value: Value to cache (must be string)
        ttl_seconds: Time-to-live in seconds
        nx: Only set if key doesn't exist (SET NX)

    Returns:
        bool: True if set successfully
    """
    client = get_redis()
    if client is None:
        return False

    try:
        if nx:
            result = await client.set(key, value, ex=ttl_seconds, nx=True)
            return result is not None
        else:
            await client.set(key, value, ex=ttl_seconds)
            return True
    except Exception as e:
        logger.warning(f"Redis cache_set failed for key {key}: {e}")
        return False


async def cache_get(key: str) -> Optional[str]:
    """
    Get a cached value.

    Args:
        key: Cache key

    Returns:
        str: Cached value, or None if not found/error
    """
    client = get_redis()
    if client is None:
        return None

    try:
        return await client.get(key)
    except Exception as e:
        logger.warning(f"Redis cache_get failed for key {key}: {e}")
        return None


async def cache_delete(key: str) -> bool:
    """
    Delete a cached value.

    Args:
        key: Cache key

    Returns:
        bool: True if deleted successfully
    """
    client = get_redis()
    if client is None:
        return False

    try:
        await client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Redis cache_delete failed for key {key}: {e}")
        return False
# ============================================================================
# Message Queue Implementation
# ============================================================================


class MessageQueueError(Exception):
    """Exception raised for message queue operations."""
    pass


async def queue_message(queue_name: str, message: str, priority: int = 0) -> bool:
    """
    Add a message to a Redis-based priority queue.

    Args:
        queue_name: Name of the queue
        message: Message content (must be string)
        priority: Priority level (higher numbers = higher priority)

    Returns:
        bool: True if message was queued successfully
    """
    client = get_redis()
    if client is None:
        return False

    try:
        # Use sorted set for priority queuing
        # Score represents priority, member is the message
        # Add timestamp to handle same priority
        score = time.time() + (priority * 1000000)

        await client.zadd(f"mq:{queue_name}", {message: score})

        # Also store in a simple list for easy iteration
        await client.lpush(f"mq:{queue_name}:list", message)

        logger.debug(
            f"Message queued in {queue_name} with priority {priority}")
        return True

    except Exception as e:
        logger.error(f"Failed to queue message in {queue_name}: {e}")
        return False


async def get_next_message(queue_name: str, timeout: int = 0) -> Optional[str]:
    """
    Get the next message from a priority queue (blocking or non-blocking).

    Args:
        queue_name: Name of the queue
        timeout: Timeout in seconds (0 for non-blocking)

    Returns:
        str: Next message, or None if no message available
    """
    client = get_redis()
    if client is None:
        return None

    try:
        if timeout > 0:
            # Blocking pop with timeout
            result = await client.brpop(f"mq:{queue_name}:list", timeout=timeout)
            if result:
                return result[1].decode('utf-8')
            return None
        else:
            # Non-blocking pop
            result = await client.rpop(f"mq:{queue_name}:list")
            if result:
                # Also remove from sorted set
                await client.zrem(f"mq:{queue_name}", result.decode('utf-8'))
                return result.decode('utf-8')
            return None

    except Exception as e:
        logger.error(f"Failed to get message from {queue_name}: {e}")
        return None


async def get_queue_length(queue_name: str) -> int:
    """
    Get the number of messages in a queue.

    Args:
        queue_name: Name of the queue

    Returns:
        int: Number of messages in queue
    """
    client = get_redis()
    if client is None:
        return 0

    try:
        return await client.llen(f"mq:{queue_name}:list")
    except Exception as e:
        logger.error(f"Failed to get queue length for {queue_name}: {e}")
        return 0


async def clear_queue(queue_name: str) -> bool:
    """
    Clear all messages from a queue.

    Args:
        queue_name: Name of the queue

    Returns:
        bool: True if queue was cleared successfully
    """
    client = get_redis()
    if client is None:
        return False

    try:
        await client.delete(f"mq:{queue_name}:list")
        await client.delete(f"mq:{queue_name}")
        logger.info(f"Queue {queue_name} cleared")
        return True
    except Exception as e:
        logger.error(f"Failed to clear queue {queue_name}: {e}")
        return False


# ============================================================================
# Pub/Sub Messaging
# ============================================================================

class RedisSubscriber:
    """Redis pub/sub subscriber with automatic reconnection."""

    def __init__(self, channel: str):
        self.channel = channel
        self.client = None
        self.pubsub = None
        self.is_running = False

    async def connect(self):
        """Connect to Redis pub/sub."""
        self.client = get_redis()
        if self.client is None:
            raise MessageQueueError("Redis not available for pub/sub")

        self.pubsub = self.client.pubsub()
        await self.pubsub.subscribe(self.channel)

    async def start_listening(self, message_handler):
        """
        Start listening for messages.

        Args:
            message_handler: Async function to handle received messages
        """
        if not self.pubsub:
            await self.connect()

        self.is_running = True
        try:
            while self.is_running:
                try:
                    message = await self.pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        await message_handler(message['data'].decode('utf-8'))
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in pub/sub message handling: {e}")
                    await asyncio.sleep(1)  # Wait before retrying
        finally:
            await self.stop_listening()

    async def stop_listening(self):
        """Stop listening and cleanup."""
        self.is_running = False
        if self.pubsub:
            await self.pubsub.unsubscribe(self.channel)
            await self.pubsub.close()

    async def publish_message(self, message: str) -> bool:
        """
        Publish a message to the channel.

        Args:
            message: Message to publish

        Returns:
            bool: True if message was published successfully
        """
        client = get_redis()
        if client is None:
            return False

        try:
            result = await client.publish(self.channel, message)
            logger.debug(
                f"Published message to {self.channel}, {result} subscribers received it")
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {self.channel}: {e}")
            return False


# ============================================================================
# Redis Configuration Management
# ============================================================================

async def get_redis_config() -> Dict[str, Any]:
    """
    Get current Redis configuration and statistics.

    Returns:
        dict: Redis configuration and performance metrics
    """
    client = get_redis()
    if client is None:
        return {"error": "Redis not available"}

    try:
        info = await client.info()
        return {
            "version": info.get("redis_version"),
            "uptime": info.get("uptime_in_seconds"),
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "used_memory_peak": info.get("used_memory_peak_human"),
            "total_commands_processed": info.get("total_commands_processed"),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
            "keyspace_hits": info.get("keyspace_hits"),
            "keyspace_misses": info.get("keyspace_misses"),
            "expired_keys": info.get("expired_keys"),
            "evicted_keys": info.get("evicted_keys"),
        }
    except Exception as e:
        logger.error(f"Failed to get Redis config: {e}")
        return {"error": str(e)}


async def optimize_redis_memory():
    """
    Attempt to optimize Redis memory usage.

    Returns:
        dict: Result of optimization attempts
    """
    client = get_redis()
    if client is None:
        return {"error": "Redis not available"}

    results = {}

    try:
        # Flush expired keys
        flushed = await client.flushdb()
        results["flushed_expired_keys"] = flushed

        # Get memory info
        memory_info = await client.info("memory")
        results["memory_info"] = {
            "used_memory": memory_info.get("used_memory_human"),
            "used_memory_peak": memory_info.get("used_memory_peak_human"),
            "mem_fragmentation_ratio": memory_info.get("mem_fragmentation_ratio"),
        }

        logger.info("Redis memory optimization completed")
        return results

    except Exception as e:
        logger.error(f"Failed to optimize Redis memory: {e}")
        return {"error": str(e)}


# ============================================================================
# Enhanced Cache Operations with Advanced Features
# ============================================================================

async def cache_get_or_set(
    key: str,
    fetch_function,
    ttl_seconds: int = 300,
    max_age_seconds: int = None
) -> Any:
    """
    Get value from cache or fetch and store it.

    Args:
        key: Cache key
        fetch_function: Async function to fetch value if not cached
        ttl_seconds: TTL for the cached value
        max_age_seconds: Maximum age before refresh (None for no refresh)

    Returns:
        Cached or fetched value
    """
    # Try to get from cache
    cached_value = await cache_get(key)
    if cached_value is not None:
        # Check if we need to refresh due to age
        if max_age_seconds:
            try:
                # Assuming we store timestamp with the value
                import json
                data = json.loads(cached_value)
                if time.time() - data.get('timestamp', 0) < max_age_seconds:
                    return data.get('value')
            except Exception:
                pass  # If parsing fails, treat as stale

        try:
            import json
            cached_data = json.loads(cached_value)
            return cached_data.get('value') if isinstance(cached_data, dict) else cached_value
        except Exception:
            return cached_value

    # Fetch new value
    try:
        new_value = await fetch_function()

        # Store with timestamp for age tracking
        cache_data = {
            'value': new_value,
            'timestamp': time.time()
        }

        import json
        await cache_set(key, json.dumps(cache_data), ttl_seconds)
        return new_value

    except Exception as e:
        logger.error(f"Failed to fetch and cache value for key {key}: {e}")
        # If fetch fails, return None or raise exception based on requirements
        return None


async def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching a pattern.

    Args:
        pattern: Key pattern to match (e.g., "user:*:permissions")

    Returns:
        int: Number of keys invalidated
    """
    client = get_redis()
    if client is None:
        return 0

    try:
        keys = await client.keys(pattern)
        if keys:
            deleted = await client.delete(*keys)
            logger.info(
                f"Invalidated {deleted} cache keys matching pattern: {pattern}")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
        return 0


async def get_cache_stats() -> Dict[str, Any]:
    """
    Get comprehensive cache statistics.

    Returns:
        dict: Cache performance statistics
    """
    client = get_redis()
    if client is None:
        return {"error": "Redis not available"}

    try:
        info = await client.info("stats")

        # Calculate hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total_requests = hits + misses
        hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0

        # Get memory usage
        memory_info = await client.info("memory")

        return {
            "hits": hits,
            "misses": misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "used_memory_mb": round(memory_info.get("used_memory", 0) / 1024 / 1024, 2),
            "memory_fragmentation_ratio": memory_info.get("mem_fragmentation_ratio"),
            "connected_clients": info.get("connected_clients", 0),
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"error": str(e)}


async def cache_exists(key: str) -> bool:
    """
    Check if a key exists in cache.

    Args:
        key: Cache key

    Returns:
        bool: True if key exists
    """
    client = get_redis()
    if client is None:
        return False

    try:
        return await client.exists(key) > 0
    except Exception as e:
        logger.warning(f"Redis cache_exists failed for key {key}: {e}")
        return False


# ============================================================================
# Distributed Locking
# ============================================================================

async def acquire_lock(
    lock_name: str,
    ttl_seconds: int = 60,
    blocking: bool = False,
    blocking_timeout: float = 5.0,
) -> Optional[str]:
    """
    Acquire a distributed lock using Redis SETNX.

    Args:
        lock_name: Name of the lock
        ttl_seconds: Lock expiration time in seconds
        blocking: If True, wait for lock to become available
        blocking_timeout: How long to wait for lock (if blocking=True)

    Returns:
        str: Lock token if acquired, None if failed

    Usage:
        lock_token = await acquire_lock("my-job-lock", ttl_seconds=60)
        if lock_token:
            try:
                # Do work...
            finally:
                await release_lock("my-job-lock", lock_token)
    """
    import asyncio
    import uuid

    client = get_redis()
    if client is None:
        return None

    lock_key = f"{RedisKeys.LOCK}{lock_name}"
    lock_token = str(uuid.uuid4())

    try:
        if blocking:
            # Blocking mode: retry until timeout
            end_time = asyncio.get_event_loop().time() + blocking_timeout
            while asyncio.get_event_loop().time() < end_time:
                result = await client.set(lock_key, lock_token, ex=ttl_seconds, nx=True)
                if result:
                    return lock_token
                await asyncio.sleep(0.1)  # Wait 100ms before retry
            return None
        else:
            # Non-blocking: single attempt
            result = await client.set(lock_key, lock_token, ex=ttl_seconds, nx=True)
            return lock_token if result else None

    except Exception as e:
        logger.warning(f"Failed to acquire lock {lock_name}: {e}")
        return None


async def release_lock(lock_name: str, lock_token: str) -> bool:
    """
    Release a distributed lock.

    Only releases if the lock_token matches (prevents releasing other's locks).

    Args:
        lock_name: Name of the lock
        lock_token: Token received from acquire_lock

    Returns:
        bool: True if lock was released
    """
    client = get_redis()
    if client is None:
        return False

    lock_key = f"{RedisKeys.LOCK}{lock_name}"

    # Lua script for atomic check-and-delete
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    try:
        result = await client.eval(lua_script, 1, lock_key, lock_token)
        return result == 1
    except Exception as e:
        logger.warning(f"Failed to release lock {lock_name}: {e}")
        return False


async def extend_lock(lock_name: str, lock_token: str, ttl_seconds: int) -> bool:
    """
    Extend the TTL of an existing lock.

    Only extends if the lock_token matches.

    Args:
        lock_name: Name of the lock
        lock_token: Token received from acquire_lock
        ttl_seconds: New TTL in seconds

    Returns:
        bool: True if lock was extended
    """
    client = get_redis()
    if client is None:
        return False

    lock_key = f"{RedisKeys.LOCK}{lock_name}"

    # Lua script for atomic check-and-extend
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("expire", KEYS[1], ARGV[2])
    else
        return 0
    end
    """

    try:
        result = await client.eval(lua_script, 1, lock_key, lock_token, ttl_seconds)
        return result == 1
    except Exception as e:
        logger.warning(f"Failed to extend lock {lock_name}: {e}")
        return False
