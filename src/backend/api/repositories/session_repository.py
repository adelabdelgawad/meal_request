"""Session Repository - Database operations for session management."""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from core.exceptions import DatabaseError, NotFoundError
from db.models import Session
from settings import settings

logger = logging.getLogger(__name__)


class SessionRepository:
    """Repository for session CRUD operations with atomic token rotation."""

    async def create_session(
        self,
        session: AsyncSession,
        user_id: str,
        refresh_token_id: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
        fingerprint: Optional[str] = None,
        metadata: Optional[dict] = None,
        locale: Optional[str] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            session: Database session
            user_id: User ID (UUID as string)
            refresh_token_id: Refresh token JTI
            expires_at: Session expiration timestamp
            device_info: User agent or device info
            ip_address: Client IP address
            fingerprint: Hashed device fingerprint
            metadata: Additional JSON metadata
            locale: User's locale preference (e.g., 'en', 'ar')

        Returns:
            Created Session object

        Raises:
            DatabaseError: If creation fails
        """
        now = datetime.now(timezone.utc)

        # Prepare metadata with locale if provided
        session_metadata = metadata or {}
        if locale:
            session_metadata['locale'] = locale

        new_session = Session(
            id=str(uuid.uuid4()),
            user_id=user_id,
            refresh_token_id=refresh_token_id,
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
            revoked=False,
            device_info=device_info,
            ip_address=ip_address,
            fingerprint=fingerprint,
            session_metadata=session_metadata,
        )

        try:
            session.add(new_session)
            await session.flush()
            return new_session
        except IntegrityError as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create session: {str(e)}")

    async def get_by_refresh_id(
        self, session: AsyncSession, refresh_token_id: str
    ) -> Optional[Session]:
        """
        Get a session by refresh token ID.

        Args:
            session: Database session
            refresh_token_id: Refresh token JTI

        Returns:
            Session object or None if not found
        """
        stmt = select(Session).where(Session.refresh_token_id == refresh_token_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_refresh_id_for_update(
        self, session: AsyncSession, refresh_token_id: str
    ) -> Optional[Session]:
        """
        Get a session by refresh token ID with SELECT FOR UPDATE lock.

        This ensures atomic token rotation by preventing concurrent updates.

        Args:
            session: Database session
            refresh_token_id: Refresh token JTI

        Returns:
            Session object or None if not found
        """
        stmt = (
            select(Session)
            .where(Session.refresh_token_id == refresh_token_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(
        self, session: AsyncSession, session_id: str
    ) -> Optional[Session]:
        """
        Get a session by ID.

        Args:
            session: Database session
            session_id: Session ID (UUID as string)

        Returns:
            Session object or None if not found
        """
        stmt = select(Session).where(Session.id == session_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def rotate_refresh_id(
        self, session: AsyncSession, old_refresh_id: str, new_refresh_id: str, locale: Optional[str] = None
    ) -> Session:
        """
        Atomically rotate refresh token ID.

        Uses SELECT FOR UPDATE to prevent race conditions during concurrent refresh requests.

        Args:
            session: Database session
            old_refresh_id: Current refresh token JTI
            new_refresh_id: New refresh token JTI
            locale: Optional locale to update in session metadata

        Returns:
            Updated Session object

        Raises:
            NotFoundError: If session not found
            DatabaseError: If update fails
        """
        # Lock the row for update
        db_session = await self.get_by_refresh_id_for_update(session, old_refresh_id)
        if not db_session:
            raise NotFoundError(entity="Session", identifier=old_refresh_id)

        # Check if session is revoked
        if db_session.revoked:
            raise DatabaseError("Cannot rotate revoked session")

        # Check if session is expired
        now = datetime.now(timezone.utc)

        # Make expires_at timezone-aware if it's naive (database stores UTC without tz info)
        expires_at = db_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            raise DatabaseError("Cannot rotate expired session")

        # Update the refresh token ID and last seen timestamp
        try:
            db_session.refresh_token_id = new_refresh_id
            db_session.last_seen_at = now

            # Update locale in metadata if provided
            if locale:
                if not db_session.session_metadata:
                    db_session.session_metadata = {}
                db_session.session_metadata['locale'] = locale
                # Mark the JSON column as modified so SQLAlchemy detects the change
                attributes.flag_modified(db_session, 'session_metadata')

            await session.flush()
            return db_session
        except IntegrityError as e:
            await session.rollback()
            raise DatabaseError(f"Failed to rotate refresh token: {str(e)}")

    async def update_last_seen(
        self, session: AsyncSession, refresh_token_id: str
    ) -> Optional[Session]:
        """
        Update the last_seen_at timestamp for a session.

        Args:
            session: Database session
            refresh_token_id: Refresh token JTI

        Returns:
            Updated Session object or None if not found
        """
        db_session = await self.get_by_refresh_id(session, refresh_token_id)
        if not db_session:
            return None

        db_session.last_seen_at = datetime.now(timezone.utc)
        await session.flush()
        return db_session

    async def revoke_session(
        self, session: AsyncSession, refresh_token_id: str
    ) -> Optional[Session]:
        """
        Revoke a session by refresh token ID.

        Also invalidates Redis cache to ensure immediate revocation effect.

        Args:
            session: Database session
            refresh_token_id: Refresh token JTI

        Returns:
            Revoked Session object or None if not found
        """
        db_session = await self.get_by_refresh_id(session, refresh_token_id)
        if not db_session:
            return None

        db_session.revoked = True
        await session.flush()

        # Invalidate session cache
        await self._invalidate_session_cache(refresh_token_id)

        return db_session

    async def revoke_by_session_id(
        self, session: AsyncSession, session_id: str
    ) -> Optional[Session]:
        """
        Revoke a session by session ID.

        Also invalidates Redis cache to ensure immediate revocation effect.

        Args:
            session: Database session
            session_id: Session ID (UUID as string)

        Returns:
            Revoked Session object or None if not found
        """
        db_session = await self.get_by_id(session, session_id)
        if not db_session:
            return None

        db_session.revoked = True
        await session.flush()

        # Invalidate session cache
        await self._invalidate_session_cache(db_session.refresh_token_id)

        return db_session

    async def revoke_by_user(
        self, session: AsyncSession, user_id: str, except_session_id: Optional[str] = None
    ) -> int:
        """
        Revoke all sessions for a user.

        Also invalidates Redis cache for all revoked sessions.

        Args:
            session: Database session
            user_id: User ID (UUID as string)
            except_session_id: Optional session ID to exclude from revocation

        Returns:
            Number of sessions revoked
        """
        stmt = select(Session).where(
            Session.user_id == user_id, ~Session.revoked
        )
        if except_session_id:
            stmt = stmt.where(Session.id != except_session_id)

        result = await session.execute(stmt)
        sessions_to_revoke = result.scalars().all()

        count = 0
        for db_session in sessions_to_revoke:
            db_session.revoked = True
            # Invalidate cache for each revoked session
            await self._invalidate_session_cache(db_session.refresh_token_id)
            count += 1

        await session.flush()
        return count

    async def list_by_user(
        self, session: AsyncSession, user_id: str, include_revoked: bool = False
    ) -> List[Session]:
        """
        List all sessions for a user.

        Args:
            session: Database session
            user_id: User ID (UUID as string)
            include_revoked: Include revoked sessions in results

        Returns:
            List of Session objects
        """
        stmt = select(Session).where(Session.user_id == user_id)
        if not include_revoked:
            stmt = stmt.where(~Session.revoked)

        stmt = stmt.order_by(Session.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_expired(self, session: AsyncSession) -> int:
        """
        Delete expired sessions.

        Args:
            session: Database session

        Returns:
            Number of sessions deleted
        """
        now = datetime.now(timezone.utc)
        stmt = select(Session).where(Session.expires_at < now)
        result = await session.execute(stmt)
        expired_sessions = result.scalars().all()

        count = 0
        for db_session in expired_sessions:
            await session.delete(db_session)
            count += 1

        await session.flush()
        return count

    async def is_session_valid(
        self, session: AsyncSession, refresh_token_id: str
    ) -> bool:
        """
        Check if a session is valid (exists, not revoked, not expired).

        Uses Redis cache for performance with database fallback.

        Cache Strategy:
        - Cache "invalid" sessions (revoked or expired) to prevent repeated DB hits
        - DON'T cache valid sessions (to detect revocation immediately)
        - Invalid sessions are cached with short TTL

        Args:
            session: Database session
            refresh_token_id: Refresh token JTI

        Returns:
            True if session is valid, False otherwise
        """
        from core.redis import RedisKeys, cache_exists, cache_set, is_redis_available

        # Check if session is cached as invalid
        if is_redis_available():
            cache_key = f"{RedisKeys.SESSION}invalid:{refresh_token_id}"
            if await cache_exists(cache_key):
                logger.debug(f"Session {refresh_token_id[:8]}... found in invalid cache")
                return False

        # Check database
        db_session = await self.get_by_refresh_id(session, refresh_token_id)
        if not db_session:
            # Cache as invalid (session doesn't exist)
            if is_redis_available():
                await cache_set(
                    f"{RedisKeys.SESSION}invalid:{refresh_token_id}",
                    "not_found",
                    settings.REDIS_SESSION_CACHE_TTL_SECONDS
                )
            return False

        if db_session.revoked:
            # Cache as invalid (session revoked)
            if is_redis_available():
                await cache_set(
                    f"{RedisKeys.SESSION}invalid:{refresh_token_id}",
                    "revoked",
                    settings.REDIS_SESSION_CACHE_TTL_SECONDS
                )
            return False

        now = datetime.now(timezone.utc)
        # Handle timezone-naive expires_at
        expires_at = db_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            # Cache as invalid (session expired)
            if is_redis_available():
                await cache_set(
                    f"{RedisKeys.SESSION}invalid:{refresh_token_id}",
                    "expired",
                    settings.REDIS_SESSION_CACHE_TTL_SECONDS
                )
            return False

        return True

    async def _invalidate_session_cache(self, refresh_token_id: str) -> None:
        """
        Invalidate session cache entry when session state changes.

        Called when a session is revoked to ensure cache consistency.

        Args:
            refresh_token_id: Refresh token JTI
        """
        from core.redis import RedisKeys, cache_set, is_redis_available

        if not is_redis_available():
            return

        # Mark session as invalid in cache
        cache_key = f"{RedisKeys.SESSION}invalid:{refresh_token_id}"
        await cache_set(cache_key, "revoked", settings.REDIS_SESSION_CACHE_TTL_SECONDS)
        logger.debug(f"Cached session {refresh_token_id[:8]}... as invalid")

    async def count_active_sessions(
        self, session: AsyncSession, user_id: str
    ) -> int:
        """
        Count active (non-revoked, non-expired) sessions for a user.

        Args:
            session: Database session
            user_id: User ID (UUID as string)

        Returns:
            Number of active sessions
        """
        now = datetime.now(timezone.utc)
        stmt = select(Session).where(
            Session.user_id == user_id,
            ~Session.revoked,
            Session.expires_at > now
        )
        result = await session.execute(stmt)
        active_sessions = result.scalars().all()
        return len(active_sessions)

    async def get_oldest_active_session(
        self, session: AsyncSession, user_id: str
    ) -> Optional[Session]:
        """
        Get the oldest active session for a user (by created_at).

        Args:
            session: Database session
            user_id: User ID (UUID as string)

        Returns:
            Oldest active Session object or None if no active sessions
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Session)
            .where(
                Session.user_id == user_id,
                ~Session.revoked,
                Session.expires_at > now
            )
            .order_by(Session.created_at.asc())  # Oldest first
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def enforce_session_limit(
        self, session: AsyncSession, user_id: str, max_sessions: int, exclude_session_id: str = None
    ) -> int:
        """
        Enforce max concurrent sessions by revoking oldest sessions if limit exceeded.

        Args:
            session: Database session
            user_id: User ID (UUID as string)
            max_sessions: Maximum allowed concurrent sessions (0 = unlimited)
            exclude_session_id: Session identifier to exclude from revocation (the current session)

        Returns:
            Number of sessions revoked (0 if limit not exceeded)

        Note:
            If max_sessions is 0 or negative, no limit is enforced.
        """
        # If unlimited sessions, do nothing
        if max_sessions <= 0:
            return 0

        # Count current active sessions
        active_count = await self.count_active_sessions(session, user_id)

        # If under or at limit, do nothing
        if active_count <= max_sessions:
            return 0

        # Calculate how many sessions to revoke
        # Since we already created the new session, just revoke the excess
        sessions_to_revoke = active_count - max_sessions

        # Revoke oldest sessions (excluding the current one)
        now = datetime.now(timezone.utc)

        # Build base query
        base_conditions = [
            Session.user_id == user_id,
            ~Session.revoked,
            Session.expires_at > now
        ]

        # Exclude the current session if specified
        if exclude_session_id:
            base_conditions.append(Session.id != exclude_session_id)

        stmt = (
            select(Session)
            .where(*base_conditions)
            .order_by(Session.created_at.asc())  # Oldest first
            .limit(sessions_to_revoke)
        )

        result = await session.execute(stmt)
        sessions_to_revoke_list = list(result.scalars().all())

        count = 0
        for db_session in sessions_to_revoke_list:
            # Log which session is being revoked for debugging
            logger.info(
                f"Revoking session id={db_session.id}, refresh_token_id={db_session.refresh_token_id}, "
                f"created_at={db_session.created_at}, exclude_id={exclude_session_id}"
            )
            db_session.revoked = True
            # Invalidate cache for each revoked session
            await self._invalidate_session_cache(db_session.refresh_token_id)
            count += 1

        await session.flush()
        return count
