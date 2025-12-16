"""Log Role Service - Business logic for role audit logging."""

import json
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_role_repository import LogRoleRepository
from api.schemas.log_role_schemas import LogRoleQuery
from db.models import LogRole

logger = logging.getLogger(__name__)


class LogRoleService:
    """Service for role audit log management operations."""

    def __init__(self):
        """Initialize service."""
        self.repository = LogRoleRepository()

    async def log_role_action(
        self,
        session: AsyncSession,
        admin_id: str,
        action: str,
        is_successful: bool,
        role_id: Optional[int] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        result: Optional[dict] = None,
    ) -> None:
        """
        Log a role management action.

        Args:
            session: Database session
            admin_id: ID of the admin performing the action
            action: Action being performed (create_role, update_role, delete_role, etc.)
            is_successful: Whether the action was successful
            role_id: ID of the role being acted upon (optional)
            old_value: Previous state (for updates/deletes)
            new_value: New state (for creates/updates)
            result: Additional result information

        Actions:
            - create_role: Creating a new role
            - update_role: Updating role information
            - delete_role: Deleting a role
            - assign_page: Assigning page permission to role
            - revoke_page: Revoking page permission from role
            - update_status: Changing role status
        """
        try:
            log_data = {
                "admin_id": admin_id,
                "role_id": role_id,
                "action": action,
                "is_successful": is_successful,
                "old_value": json.dumps(old_value) if old_value else None,
                "new_value": json.dumps(new_value) if new_value else None,
                "result": json.dumps(result) if result else None,
            }
            await self.repository.create(session, log_data)
        except Exception as e:
            # Log the error but don't fail the operation
            logger.error(f"Failed to log role action: {e}", exc_info=True)

    async def get_log(self, session: AsyncSession, log_id: str) -> Optional[LogRole]:
        """Get a role audit log by ID."""
        return await self.repository.get_by_id(session, log_id)

    async def list_logs(
        self,
        session: AsyncSession,
        query: LogRoleQuery,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[LogRole], int]:
        """List role audit logs with filtering."""
        return await self.repository.list(
            session=session,
            page=page,
            per_page=per_page,
            admin_id=query.admin_id,
            role_id=query.role_id,
            action=query.action,
            from_date=query.from_date,
            to_date=query.to_date,
        )

    async def get_role_history(
        self,
        session: AsyncSession,
        role_id: int,
        limit: int = 50
    ) -> List[LogRole]:
        """Get audit history for a specific role."""
        return await self.repository.get_by_role_id(session, role_id, limit)

    async def get_admin_actions(
        self,
        session: AsyncSession,
        admin_id: str,
        limit: int = 50
    ) -> List[LogRole]:
        """Get audit logs for a specific admin."""
        return await self.repository.get_by_admin_id(session, admin_id, limit)
