"""RevokedToken Service - Business logic for token revocation."""

import logging
from datetime import datetime, timedelta
from uuid import UUID

import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.revoked_token_repository import RevokedTokenRepository
from core.security import create_jwt
from db.models import RevokedToken
from settings import settings

logger = logging.getLogger(__name__)


class RevokedTokenService:
    """Service for token revocation and JWT management."""

    def __init__(self):
        self._repo = RevokedTokenRepository()

    async def revoke_token(
        self,
        session: AsyncSession,
        jti: str,
        token_type: str,
        user_id: str = None,
        account_id: int = None,
        expires_at: datetime = None,
    ) -> RevokedToken:
        """
        Revoke a JWT token by storing its JTI and caching in Redis.

        Args:
            session: Database session
            jti: JWT ID from the token
            token_type: 'access' or 'refresh'
            user_id: User ID who owns the token (UUID as string)
            account_id: User ID (deprecated parameter, kept for backward compatibility)
            expires_at: When the token expires

        Returns:
            RevokedToken record
        """
        # Convert user_id string to UUID if provided
        user_uuid = UUID(user_id) if user_id and isinstance(user_id, str) else user_id

        token = RevokedToken(
            jti=jti,
            token_type=token_type,
            user_id=user_uuid,
            account_id=account_id,
            expires_at=expires_at,
            revoked_at=datetime.now(pytz.timezone("Africa/Cairo")),
        )
        result = await self._repo.create(session, token)

        # Cache the revoked token in Redis for fast lookups
        await self._cache_revoked_token(jti, expires_at)

        return result

    async def _cache_revoked_token(
        self, jti: str, expires_at: datetime = None
    ) -> None:
        """
        Cache a revoked token JTI in Redis.

        TTL is calculated based on token expiration or defaults to configured value.

        Args:
            jti: JWT ID to cache
            expires_at: Token expiration time (for TTL calculation)
        """
        from core.redis import RedisKeys, cache_set, is_redis_available

        if not is_redis_available():
            return

        # Calculate TTL based on token expiration
        if expires_at:
            now = datetime.now(pytz.timezone("Africa/Cairo"))
            if expires_at.tzinfo is None:
                # Assume Cairo timezone if not specified
                expires_at = pytz.timezone("Africa/Cairo").localize(expires_at)
            remaining_seconds = int((expires_at - now).total_seconds())
            # Use remaining time or configured TTL, whichever is smaller
            ttl = max(1, min(remaining_seconds, settings.REDIS_REVOKED_TOKEN_TTL_SECONDS))
        else:
            ttl = settings.REDIS_REVOKED_TOKEN_TTL_SECONDS

        cache_key = RedisKeys.revoked_token(jti)
        cached = await cache_set(cache_key, "1", ttl)
        if cached:
            logger.debug(f"Cached revoked token {jti[:8]}... with TTL {ttl}s")

    async def is_token_revoked(self, session: AsyncSession, jti: str) -> bool:
        """Check if a token has been revoked."""
        return await self._repo.is_revoked(session, jti)

    async def store_refresh_token(
        self,
        session: AsyncSession,
        jti: str,
        token_type: str,
        user_id: str = None,
        account_id: int = None,
        expires_at: datetime = None,
    ) -> RevokedToken:
        """
        Store a refresh token in the database for later revocation checking.

        Args:
            session: Database session
            jti: JWT ID
            token_type: Type of token ('refresh' or 'access')
            user_id: User ID that owns this token (UUID as string)
            account_id: User ID (deprecated parameter, kept for backward compatibility)
            expires_at: When the token expires

        Returns:
            RevokedToken record
        """
        token = RevokedToken(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
        )
        return await self._repo.create(session, token)

    async def create_token_pair(
        self,
        user_id: UUID,
        username: str,
        access_expires: timedelta = None,
        refresh_expires: timedelta = None,
    ) -> tuple[str, str, str, str]:
        """
        Create access and refresh token pair.

        Args:
            user_id: User ID
            username: Username
            access_expires: Optional access token expiration delta
            refresh_expires: Optional refresh token expiration delta

        Returns:
            Tuple of (access_token, access_jti, refresh_token, refresh_jti)
        """
        access_token, access_jti = create_jwt(
            data={"user_id": str(user_id), "username": username},
            token_type="access",
            expires_delta=access_expires,
        )

        refresh_token, refresh_jti = create_jwt(
            data={"user_id": str(user_id), "username": username},
            token_type="refresh",
            expires_delta=refresh_expires,
        )

        return access_token, access_jti, refresh_token, refresh_jti
