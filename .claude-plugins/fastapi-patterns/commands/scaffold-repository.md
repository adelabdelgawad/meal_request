---
description: Generate a repository layer class for data access
---

# Scaffold Repository

Generate a repository class that handles database operations.

## Instructions

When the user wants to create a repository for a resource, create the following file:

### Repository File: `src/backend/api/repositories/{resource}_repository.py`

```python
"""
Repository for {Resource} data access.

Repositories handle database operations only - no business logic.
All methods should be async and use the passed session.
"""

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, DatabaseError
from core.pagination import calculate_offset
from db.models import {Resource}


class {Resource}Repository:
    """Repository for {Resource} database operations."""

    def __init__(self):
        """Initialize repository.

        Note: Stateless - no dependencies stored.
        """
        pass

    async def create(
        self,
        session: AsyncSession,
        entity: {Resource},
    ) -> {Resource}:
        """Create a new {resource}.

        Args:
            session: Database session
            entity: {Resource} entity to create

        Returns:
            Created entity with generated ID

        Raises:
            ConflictError: If unique constraint violated
            DatabaseError: If other database error occurs
        """
        try:
            session.add(entity)
            await session.flush()
            await session.refresh(entity)
            return entity
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig).lower()
            if "duplicate" in error_msg or "unique" in error_msg:
                raise ConflictError(
                    entity="{Resource}",
                    field="name_en",
                    value=entity.name_en,
                )
            raise DatabaseError(f"Failed to create {resource}: {{str(e)}}")

    async def get_by_id(
        self,
        session: AsyncSession,
        {resource}_id: str,
    ) -> Optional[{Resource}]:
        """Get {resource} by ID.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}

        Returns:
            {Resource} entity or None if not found
        """
        result = await session.execute(
            select({Resource}).where({Resource}.id == {resource}_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
    ) -> Optional[{Resource}]:
        """Get {resource} by name (English).

        Args:
            session: Database session
            name: Name to search for

        Returns:
            {Resource} entity or None if not found
        """
        result = await session.execute(
            select({Resource}).where({Resource}.name_en == name)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[{Resource}], int]:
        """List {resources} with filtering and pagination.

        Args:
            session: Database session
            page: Page number (1-indexed)
            per_page: Items per page
            is_active: Filter by active status
            search: Search term for name fields

        Returns:
            Tuple of (list of entities, total count)
        """
        # Base query
        stmt = select({Resource})

        # Apply filters
        if is_active is not None:
            stmt = stmt.where({Resource}.is_active == is_active)

        if search:
            search_term = f"%{{search}}%"
            stmt = stmt.where(
                or_(
                    {Resource}.name_en.ilike(search_term),
                    {Resource}.name_ar.ilike(search_term),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = calculate_offset(page, per_page)
        stmt = stmt.offset(offset).limit(per_page)

        # Order by created_at descending (newest first)
        stmt = stmt.order_by({Resource}.created_at.desc())

        # Execute
        result = await session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update(
        self,
        session: AsyncSession,
        {resource}_id: str,
        update_data: Dict[str, Any],
    ) -> {Resource}:
        """Update {resource} with given data.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}
            update_data: Dictionary of fields to update

        Returns:
            Updated entity

        Raises:
            ConflictError: If update violates unique constraint
        """
        entity = await self.get_by_id(session, {resource}_id)
        if not entity:
            return None

        try:
            for key, value in update_data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            await session.flush()
            await session.refresh(entity)
            return entity
        except IntegrityError as e:
            await session.rollback()
            raise ConflictError(
                entity="{Resource}",
                field="name_en",
                value=update_data.get("name_en", "unknown"),
            )

    async def delete(
        self,
        session: AsyncSession,
        {resource}_id: str,
    ) -> bool:
        """Delete {resource} by ID.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}

        Returns:
            True if deleted, False if not found
        """
        entity = await self.get_by_id(session, {resource}_id)
        if not entity:
            return False

        await session.delete(entity)
        await session.flush()
        return True

    async def bulk_update_status(
        self,
        session: AsyncSession,
        ids: List[str],
        is_active: bool,
    ) -> List[{Resource}]:
        """Bulk update status for multiple {resources}.

        Args:
            session: Database session
            ids: List of {resource} IDs
            is_active: New status value

        Returns:
            List of updated entities
        """
        result = await session.execute(
            select({Resource}).where({Resource}.id.in_(ids))
        )
        entities = list(result.scalars().all())

        for entity in entities:
            entity.is_active = is_active

        await session.flush()
        return entities

    async def count(
        self,
        session: AsyncSession,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count {resources} with optional filter.

        Args:
            session: Database session
            is_active: Filter by active status

        Returns:
            Count of matching {resources}
        """
        stmt = select(func.count()).select_from({Resource})
        if is_active is not None:
            stmt = stmt.where({Resource}.is_active == is_active)

        result = await session.execute(stmt)
        return result.scalar() or 0
```

## Key Patterns

### DO:
- All methods must be `async`
- Pass `session` as first parameter
- Use `session.flush()` instead of `session.commit()`
- Use `session.refresh(entity)` after modifications
- Handle `IntegrityError` and convert to domain exceptions
- Return `None` for not found (let service raise NotFoundError)
- Use `select()` function from SQLAlchemy 2.0+

### DON'T:
- Store session as instance variable
- Call `session.commit()` (session manager handles this)
- Raise HTTP exceptions
- Implement business logic (that belongs in services)
- Use legacy Query API (use select() instead)
