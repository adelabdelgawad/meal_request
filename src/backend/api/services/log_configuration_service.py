"""Log Configuration Service - Business logic for configuration audit logging."""

import json
import logging
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.log_configuration_repository import LogConfigurationRepository
from api.schemas.log_configuration_schemas import (
    LogConfigurationQuery
)
from db.models import LogConfiguration

logger = logging.getLogger(__name__)


class LogConfigurationService:
    """Service for configuration audit log management operations."""

    def __init__(self):
        """Initialize service."""
        self.repository = LogConfigurationRepository()

    async def log_configuration(
        self,
        session: AsyncSession,
        admin_id: str,
        entity_type: str,
        action: str,
        is_successful: bool,
        entity_id: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        result: Optional[dict] = None,
    ) -> None:
        """
        Log a configuration change.

        Args:
            session: Database session
            admin_id: ID of the admin performing the action
            entity_type: Type of entity being modified (meal_type, department, page, etc.)
            action: Action being performed (create, update, delete)
            is_successful: Whether the action was successful
            entity_id: ID of the entity being acted upon (optional)
            old_value: Previous state (for updates/deletes)
            new_value: New state (for creates/updates)
            result: Additional result information

        Entity Types:
            - meal_type: Meal type configuration
            - department: Department configuration
            - page: Page configuration
            - user_department_assignment: User-department assignments
        """
        try:
            log_data = {
                "admin_id": admin_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "is_successful": is_successful,
                "old_value": json.dumps(old_value) if old_value else None,
                "new_value": json.dumps(new_value) if new_value else None,
                "result": json.dumps(result) if result else None,
            }
            await self.repository.create(session, log_data)
        except Exception as e:
            # Log the error but don't fail the operation
            logger.error(f"Failed to log configuration change: {e}", exc_info=True)

    async def get_log(self, session: AsyncSession, log_id: str) -> Optional[LogConfiguration]:
        """Get a configuration audit log by ID."""
        return await self.repository.get_by_id(session, log_id)

    async def list_logs(
        self,
        session: AsyncSession,
        query: LogConfigurationQuery,
        page: int = 1,
        per_page: int = 25,
    ) -> Tuple[List[LogConfiguration], int]:
        """List configuration audit logs with filtering."""
        return await self.repository.list(
            session=session,
            page=page,
            per_page=per_page,
            admin_id=query.admin_id,
            entity_type=query.entity_type,
            entity_id=query.entity_id,
            action=query.action,
            from_date=query.from_date,
            to_date=query.to_date,
        )

    async def get_entity_history(
        self,
        session: AsyncSession,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> List[LogConfiguration]:
        """Get audit history for a specific entity."""
        return await self.repository.get_by_entity(session, entity_type, entity_id, limit)

    async def get_entity_type_history(
        self,
        session: AsyncSession,
        entity_type: str,
        limit: int = 100
    ) -> List[LogConfiguration]:
        """Get audit history for all entities of a specific type."""
        return await self.repository.get_by_entity_type(session, entity_type, limit)

    async def get_admin_actions(
        self,
        session: AsyncSession,
        admin_id: str,
        limit: int = 50
    ) -> List[LogConfiguration]:
        """Get audit logs for a specific admin."""
        return await self.repository.get_by_admin_id(session, admin_id, limit)
