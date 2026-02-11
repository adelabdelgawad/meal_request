"""Log Authentication Service - Business logic for authentication audit logging."""

import json
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_authentication_repository import LogAuthenticationRepository
from api.schemas.log_authentication_schemas import LogAuthenticationCreate
from db.model import LogAuthentication

logger = logging.getLogger(__name__)


class LogAuthenticationService:
    """Service for authentication audit log management operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service."""
        self.session = session
        self.repository = LogAuthenticationRepository(session)

    async def log_authentication(
        self,
        user_id: Optional[str],
        action: str,
        is_successful: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        result: Optional[dict] = None,
    ) -> None:
        """
        Log an authentication event. Non-blocking - errors are logged but don't fail operation.

        Args:
            user_id: User ID (UUID as string, None for failed logins)
            action: Action type (login_success, login_failed, token_refresh, logout)
            is_successful: Whether action was successful
            ip_address: Client IP address
            user_agent: User agent string
            device_fingerprint: Hashed device fingerprint
            result: Additional data as dict (will be JSON serialized)
        """
        try:
            log_data = LogAuthenticationCreate(
                user_id=user_id,
                action=action,
                is_successful=is_successful,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                result=json.dumps(result) if result else None,
            )
            await self.repository.create(session, log_data)
            logger.debug(
                f"Logged authentication event: action={action}, user_id={user_id}, success={is_successful}"
            )
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Failed to log authentication event: {e}", exc_info=True)

    async def get_log(
        self, session: AsyncSession, log_id: str
    ) -> Optional[LogAuthentication]:
        """
        Get an authentication log by ID.

        Args:
            session: Database session
            log_id: Log ID (UUID as string)

        Returns:
            LogAuthentication object or None if not found
        """
        return await self.repository.get_by_id(session, log_id)

    async def query_logs(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        is_successful: Optional[bool] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Tuple[List[LogAuthentication], int]:
        """
        Query authentication logs with filters.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            user_id: Filter by user ID
            action: Filter by action type
            is_successful: Filter by success status
            from_date: Filter by start date (ISO format)
            to_date: Filter by end date (ISO format)

        Returns:
            Tuple of (list of logs, total count)
        """
        return await self.repository.query(
            page=page,
            per_page=per_page,
            user_id=user_id,
            action=action,
            is_successful=is_successful,
            from_date=from_date,
            to_date=to_date,
        )

    async def get_recent_logs(
        self, user_id: Optional[str] = None, limit: int = 10
    ) -> List[LogAuthentication]:
        """
        Get recent authentication logs for dashboard.

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of logs to return

        Returns:
            List of recent LogAuthentication objects
        """
        return await self.repository.get_recent(user_id=user_id, limit=limit)
