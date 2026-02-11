"""
Non-blocking Active Directory Authentication Client

This module provides a thread-safe, non-blocking interface to Active Directory
authentication that prevents blocking the FastAPI event loop.

Key Features:
- Thread offloading for sync ldap3 operations
- Configurable timeouts (connect, read, overall)
- Circuit breaker for fail-fast behavior
- Concurrency limiting via semaphore
- Comprehensive error handling and logging

Usage:
    client = ADAuthClient()
    try:
        user_attrs = await client.authenticate(username, password)
        if user_attrs:
            # User authenticated successfully
            pass
    except ADAuthTimeout:
        # AD timed out
        pass
    except ADAuthUnavailable:
        # Circuit breaker open or AD down
        pass
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

from ldap3 import ALL, SIMPLE, Connection, Server
from ldap3.core.exceptions import LDAPException
from starlette.concurrency import run_in_threadpool

from core.config import settings
from utils.app_schemas import UserAttributes
from utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
)


logger = logging.getLogger(__name__)


# Custom exceptions
class ADAuthError(Exception):
    """Base exception for AD authentication errors."""

    pass


class ADAuthTimeout(ADAuthError):
    """Raised when AD authentication times out."""

    pass


class ADAuthUnavailable(ADAuthError):
    """Raised when AD is unavailable (circuit breaker open)."""

    pass


class ADAuthFailed(ADAuthError):
    """Raised when authentication fails (invalid credentials)."""

    pass


@dataclass
class ADConfig:
    """Configuration for AD connection."""

    domain: str
    server: str
    port: int = 389
    use_ssl: bool = False
    connect_timeout: float = 3.0  # seconds
    receive_timeout: float = 3.0  # seconds
    overall_timeout: float = 5.0  # seconds


class ADAuthClient:
    """
    Non-blocking Active Directory authentication client.

    This client offloads synchronous ldap3 operations to a threadpool
    to prevent blocking the async event loop.
    """

    def __init__(
        self,
        config: Optional[ADConfig] = None,
        max_concurrent: int = 20,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize AD client.

        Args:
            config: AD configuration (uses settings if not provided)
            max_concurrent: Max concurrent AD authentication calls
            circuit_breaker_config: Circuit breaker configuration
        """
        self.config = config or ADConfig(
            domain=settings.ldap.domain,
            server=settings.ldap.server,
            connect_timeout=settings.ldap.connect_timeout,
            receive_timeout=settings.ldap.read_timeout,
            overall_timeout=settings.ldap.overall_timeout,
        )

        # Concurrency limiter
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # Circuit breaker
        cb_config = circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=5, success_threshold=2, timeout_seconds=30.0
        )
        self._circuit_breaker = CircuitBreaker("ad_auth", cb_config)

        logger.info(
            f"AD client initialized: "
            f"server={self.config.server}, "
            f"max_concurrent={max_concurrent}, "
            f"timeout={self.config.overall_timeout}s"
        )

    async def authenticate(
        self, username: str, password: str
    ) -> Optional[UserAttributes]:
        """
        Authenticate user against Active Directory (non-blocking).

        This method:
        1. Limits concurrency via semaphore
        2. Offloads sync ldap3 call to threadpool
        3. Enforces overall timeout
        4. Uses circuit breaker for fail-fast

        Args:
            username: Username to authenticate
            password: User's password

        Returns:
            UserAttributes if authenticated, None if invalid credentials

        Raises:
            ADAuthTimeout: If authentication times out
            ADAuthUnavailable: If circuit breaker is open
            ADAuthError: For other authentication errors
        """
        # Acquire semaphore to limit concurrency
        async with self._semaphore:
            try:
                # Use circuit breaker
                result = await self._circuit_breaker.call(
                    self._authenticate_with_timeout, username, password
                )
                return result

            except CircuitBreakerError as e:
                logger.warning(f"Circuit breaker open for AD auth: {e}")
                raise ADAuthUnavailable("AD authentication service unavailable") from e

            except asyncio.TimeoutError as e:
                logger.error(
                    f"AD authentication timeout for user '{username}' "
                    f"after {self.config.overall_timeout}s"
                )
                raise ADAuthTimeout(
                    f"AD authentication timed out after {self.config.overall_timeout}s"
                ) from e

            except ADAuthFailed:
                # Invalid credentials - not an error, just failed auth
                logger.info(
                    f"Authentication failed for user '{username}' (invalid credentials)"
                )
                return None

            except Exception as e:
                logger.error(
                    f"Unexpected error during AD authentication for '{username}': {e}",
                    exc_info=True,
                )
                raise ADAuthError(f"AD authentication error: {str(e)}") from e

    async def _authenticate_with_timeout(
        self, username: str, password: str
    ) -> Optional[UserAttributes]:
        """
        Authenticate with overall timeout wrapper.

        Args:
            username: Username
            password: Password

        Returns:
            UserAttributes if authenticated, None otherwise

        Raises:
            asyncio.TimeoutError: If overall timeout exceeded
        """
        try:
            return await asyncio.wait_for(
                self._authenticate_sync_offloaded(username, password),
                timeout=self.config.overall_timeout,
            )
        except asyncio.TimeoutError:
            logger.error(
                f"Overall timeout ({self.config.overall_timeout}s) exceeded "
                f"for user '{username}'"
            )
            raise

    async def _authenticate_sync_offloaded(
        self, username: str, password: str
    ) -> Optional[UserAttributes]:
        """
        Offload synchronous AD bind to threadpool.

        Args:
            username: Username
            password: Password

        Returns:
            UserAttributes if authenticated, None otherwise

        Raises:
            ADAuthFailed: If credentials invalid
            ADAuthError: For other errors
        """
        # Offload sync operation to threadpool
        authenticated = await run_in_threadpool(
            self._sync_authenticate, username, password
        )

        if not authenticated:
            raise ADAuthFailed("Invalid credentials")

        # Fetch user attributes (using async bonsai client if available)
        try:
            from utils.ldap import get_user_attributes

            user_attrs = await get_user_attributes(username)
            return user_attrs
        except Exception as e:
            logger.warning(
                f"Failed to fetch user attributes for '{username}': {e}. "
                f"Returning basic auth success."
            )
            # Return minimal attributes if fetch fails
            return UserAttributes(
                display_name=username, mail=None, telephone=None, title=None
            )

    def _sync_authenticate(self, username: str, password: str) -> bool:
        """
        Synchronous LDAP bind operation (runs in threadpool).

        This is the ONLY place where blocking ldap3 operations occur.
        It is NEVER called directly from async code - only via run_in_threadpool.

        Args:
            username: Username
            password: Password

        Returns:
            True if authenticated, False otherwise
        """
        connection = None
        try:
            # Create server with connect timeout
            server = Server(
                self.config.server,
                port=self.config.port,
                use_ssl=self.config.use_ssl,
                get_info=ALL,
                connect_timeout=self.config.connect_timeout,
            )

            # Create connection with receive timeout
            connection = Connection(
                server,
                user=f"{username}@{self.config.domain}",
                password=password,
                authentication=SIMPLE,
                auto_bind=False,  # Manual bind for better error handling
                receive_timeout=self.config.receive_timeout,
            )

            # Perform bind (this is the blocking operation)
            success = connection.bind()

            if success:
                logger.debug(f"AD bind successful for user '{username}'")
                return True
            else:
                logger.info(
                    f"AD bind failed for user '{username}': {connection.result}"
                )
                return False

        except LDAPException as e:
            logger.warning(
                f"LDAP exception during authentication for '{username}': {e}"
            )
            return False

        except Exception as e:
            logger.error(
                f"Unexpected error in sync AD bind for '{username}': {e}", exc_info=True
            )
            raise ADAuthError(f"AD bind error: {str(e)}") from e

        finally:
            if connection:
                try:
                    connection.unbind()
                except Exception as e:
                    logger.debug(f"Error unbinding connection: {e}")

    def get_status(self) -> dict:
        """Get current AD client status and metrics."""
        return {
            "config": {
                "server": self.config.server,
                "domain": self.config.domain,
                "timeouts": {
                    "connect": self.config.connect_timeout,
                    "receive": self.config.receive_timeout,
                    "overall": self.config.overall_timeout,
                },
            },
            "concurrency": {
                "max": self._semaphore._value,
                "available": self._semaphore._value - len(self._semaphore._waiters)
                if self._semaphore._waiters
                else self._semaphore._value,
            },
            "circuit_breaker": self._circuit_breaker.get_state(),
        }


# Global instance (lazy-initialized)
_global_ad_client: Optional[ADAuthClient] = None


def get_ad_client() -> ADAuthClient:
    """
    Get or create global AD client instance.

    Returns:
        Global ADAuthClient instance
    """
    global _global_ad_client
    if _global_ad_client is None:
        _global_ad_client = ADAuthClient()
    return _global_ad_client
