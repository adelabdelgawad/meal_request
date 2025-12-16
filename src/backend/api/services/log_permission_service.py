"""Log Permission Service - Business logic for permission logging."""

from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_permission_repository import LogPermissionRepository
from core.exceptions import NotFoundError
from db.models import LogPermission


class LogPermissionService:
    """Service for permission log management operations."""

    def __init__(self):
        """Initialize service."""
        self._repo = LogPermissionRepository()

    async def log_permission_action(
        self,
        session: AsyncSession,
        account_id: int,
        role_id: int,
        admin_id: int,
        action: str,
        is_successful: bool,
        result: Optional[str] = None,
    ) -> LogPermission:
        """Log a permission action."""
        log = LogPermission(
            account_id=account_id,
            role_id=role_id,
            admin_id=admin_id,
            action=action,
            is_successful=is_successful,
            result=result,
        )
        return await self._repo.create(session, log)

    async def get_log(self, session: AsyncSession, log_id: int) -> LogPermission:
        """Get a permission log by ID."""
        log = await self._repo.get_by_id(session, log_id)
        if not log:
            raise NotFoundError(entity="LogPermission", identifier=log_id)
        return log

    async def list_logs(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        account_id: Optional[int] = None,
        admin_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> Tuple[List[LogPermission], int]:
        """List permission logs with optional filtering."""
        return await self._repo.list(session, 
            page=page,
            per_page=per_page,
            account_id=account_id,
            admin_id=admin_id,
            action=action,
        )

    async def delete_log(self, session: AsyncSession, log_id: int) -> None:
        """Delete a permission log."""
        await self._repo.delete(session, log_id)
