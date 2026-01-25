---
description: Generate a service layer class following established patterns
---

# Scaffold Service

Generate a service layer class that handles business logic and coordinates with repositories.

## Instructions

When the user wants to create a service for a resource, create the following file:

### Service File: `src/backend/api/services/{resource}_service.py`

```python
"""
Service layer for {Resource} management.

Services handle business logic and coordinate with repositories.
They should NOT store sessions as instance variables.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.{resource}_repository import {Resource}Repository
from api.schemas.{resource} import {Resource}Create, {Resource}Update
from core.exceptions import NotFoundError, ConflictError, ValidationError
from db.models import {Resource}


class {Resource}Service:
    """Service for {resource} operations."""

    def __init__(self):
        """Initialize service with repository dependencies.

        Note: Session is NOT stored here - it's passed to each method.
        """
        self._repo = {Resource}Repository()

    async def create(
        self,
        session: AsyncSession,
        data: {Resource}Create,
    ) -> {Resource}:
        """Create a new {resource}.

        Args:
            session: Database session (passed per-request)
            data: Validated creation data

        Returns:
            Created {resource} entity

        Raises:
            ConflictError: If {resource} with same identifier exists
            ValidationError: If data is invalid
        """
        # 1. Validate business rules
        errors = []
        if not data.name_en or len(data.name_en.strip()) == 0:
            errors.append({{"field": "name_en", "message": "Name is required"}})

        if errors:
            raise ValidationError(errors=errors)

        # 2. Check for conflicts (unique constraints)
        existing = await self._repo.get_by_name(session, data.name_en)
        if existing:
            raise ConflictError(
                entity="{Resource}",
                field="name_en",
                value=data.name_en,
            )

        # 3. Create entity
        entity = {Resource}(
            name_en=data.name_en.strip(),
            name_ar=data.name_ar.strip() if data.name_ar else None,
            description_en=data.description_en,
            description_ar=data.description_ar,
            is_active=data.is_active,
        )

        # 4. Persist via repository
        created = await self._repo.create(session, entity)

        # 5. Post-creation logic (if any)
        # e.g., send notifications, create related records

        return created

    async def get_by_id(
        self,
        session: AsyncSession,
        {resource}_id: str,
    ) -> {Resource}:
        """Get {resource} by ID.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}

        Returns:
            {Resource} entity

        Raises:
            NotFoundError: If {resource} not found
        """
        entity = await self._repo.get_by_id(session, {resource}_id)
        if not entity:
            raise NotFoundError(entity="{Resource}", identifier={resource}_id)
        return entity

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
            Tuple of (items, total_count)
        """
        filters = {{}}
        if is_active is not None:
            filters["is_active"] = is_active
        if search:
            filters["search"] = search

        return await self._repo.list(
            session,
            page=page,
            per_page=per_page,
            **filters,
        )

    async def update(
        self,
        session: AsyncSession,
        {resource}_id: str,
        data: {Resource}Update,
    ) -> {Resource}:
        """Update a {resource}.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}
            data: Validated update data (partial)

        Returns:
            Updated {resource} entity

        Raises:
            NotFoundError: If {resource} not found
            ConflictError: If update would violate constraints
        """
        # 1. Ensure entity exists
        entity = await self.get_by_id(session, {resource}_id)

        # 2. Build update dict (only non-None fields)
        updates = {{}}
        if data.name_en is not None:
            updates["name_en"] = data.name_en.strip()
        if data.name_ar is not None:
            updates["name_ar"] = data.name_ar.strip() if data.name_ar else None
        if data.description_en is not None:
            updates["description_en"] = data.description_en
        if data.description_ar is not None:
            updates["description_ar"] = data.description_ar
        if data.is_active is not None:
            updates["is_active"] = data.is_active

        if not updates:
            return entity  # Nothing to update

        # 3. Check for conflicts if name changed
        if "name_en" in updates:
            existing = await self._repo.get_by_name(session, updates["name_en"])
            if existing and str(existing.id) != {resource}_id:
                raise ConflictError(
                    entity="{Resource}",
                    field="name_en",
                    value=updates["name_en"],
                )

        # 4. Persist updates
        return await self._repo.update(session, {resource}_id, updates)

    async def delete(
        self,
        session: AsyncSession,
        {resource}_id: str,
    ) -> bool:
        """Delete a {resource}.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}

        Returns:
            True if deleted

        Raises:
            NotFoundError: If {resource} not found
        """
        # Ensure exists
        await self.get_by_id(session, {resource}_id)

        # Soft delete or hard delete based on requirements
        return await self._repo.delete(session, {resource}_id)

    async def toggle_status(
        self,
        session: AsyncSession,
        {resource}_id: str,
        is_active: bool,
    ) -> {Resource}:
        """Toggle {resource} active status.

        Args:
            session: Database session
            {resource}_id: UUID of the {resource}
            is_active: New status

        Returns:
            Updated {resource} entity
        """
        entity = await self.get_by_id(session, {resource}_id)
        return await self._repo.update(
            session,
            {resource}_id,
            {{"is_active": is_active}},
        )
```

## Key Patterns

### DO:
- Pass `session` as first parameter to all methods
- Instantiate repositories in `__init__`
- Raise domain exceptions (NotFoundError, ConflictError, ValidationError)
- Validate business rules before persistence
- Use docstrings with Args, Returns, Raises sections

### DON'T:
- Store session as `self.session` or `self._session`
- Raise `HTTPException` (that's for routers only)
- Call `session.commit()` (let the session manager handle it)
- Put HTTP-specific logic in services
