"""
Base Repository

Generic repository base class providing common CRUD operations.
All repositories should inherit from BaseRepository[T] where T is a SQLAlchemy model.
"""

from typing import Generic, Type, TypeVar, overload
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select

T = TypeVar("T", bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """
    Generic base repository for common CRUD operations.

    All repositories inherit from this class to get standard database operations.
    The model class must be set as a class attribute (e.g., `model = User`).

    Transaction Control:
        - create(): flush + refresh, NO commit (caller must commit)
        - delete(): marks for deletion, NO commit (caller must commit)
        - All other methods: read-only, no transaction control
    """

    model: Type[T]

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize repository with a database session.

        Args:
            session: Async SQLAlchemy session for database operations
        """
        self.session = session

    @overload
    async def get_by_id(self, id: int) -> T | None: ...

    @overload
    async def get_by_id(self, id: UUID) -> T | None: ...

    @overload
    async def get_by_id(self, id: str) -> T | None: ...

    async def get_by_id(self, id: int | UUID | str) -> T | None:
        """
        Get a single entity by primary key ID.

        Args:
            id: Primary key value (int, UUID, or str for CHAR(36) columns)

        Returns:
            The entity if found, None otherwise
        """
        return await self.session.get(self.model, id)

    async def create(self, entity: T) -> T:
        """
        Create a new entity in the database.

        Flushes and refreshes to get generated IDs, but does NOT commit.
        Caller must commit the transaction.

        Args:
            entity: The entity instance to create

        Returns:
            The entity with generated ID populated
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """
        Mark an entity for deletion.

        Does NOT commit. Caller must commit the transaction.

        Args:
            entity: The entity instance to delete
        """
        await self.session.delete(entity)

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """
        List all entities with optional pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result.all())
