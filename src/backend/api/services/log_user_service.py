"""
User Management Audit Log Service - Stream 4

Business logic for logging user management operations.
"""

import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_user_repository import LogUserRepository
from api.schemas.log_user_schemas import LogUserCreate

logger = logging.getLogger(__name__)


class LogUserService:
    """Service for user management audit logging."""

    def __init__(self):
        self.repository = LogUserRepository()

    async def log_user_action(
        self,
        session: AsyncSession,
        admin_id: str,
        action: str,
        is_successful: bool,
        target_user_id: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        result: Optional[dict] = None,
    ) -> None:
        """
        Log a user management action. Non-blocking - failures are silently caught.

        Args:
            session: Database session
            admin_id: ID of the admin performing the action
            action: Action type (create, update_profile, update_status, delete, role_assignment)
            is_successful: Whether the action succeeded
            target_user_id: ID of the user being managed (None for create before user exists)
            old_value: Previous values (dict, will be JSON serialized)
            new_value: New values (dict, will be JSON serialized)
            result: Result details (dict, will be JSON serialized)
        """
        try:
            log_data = LogUserCreate(
                admin_id=admin_id,
                target_user_id=target_user_id,
                action=action,
                is_successful=is_successful,
                old_value=json.dumps(old_value) if old_value else None,
                new_value=json.dumps(new_value) if new_value else None,
                result=json.dumps(result) if result else None,
            )
            await self.repository.create(session, log_data)
        except Exception as e:
            # Log errors but don't fail the operation
            logger.error(f"Failed to log user action: {e}", exc_info=True)
