import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings as app_settings

logger = logging.getLogger(__name__)

# Build database URL from settings - use PostgreSQL
# Fallback to PostgreSQL with default credentials
DATABASE_URL = app_settings.database.url or os.getenv(
    "POSTGRES_URL",
    "postgresql+asyncpg://meal_user:meal_password@localhost:5432/meal_request_db",
)

# Create async engine and session factory
# PostgreSQL-specific settings optimized for asyncpg driver
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # Detect stale connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    max_overflow=20,  # Allow 20 additional connections when pool is full
    pool_size=10,  # Base pool size
    connect_args={
        "server_settings": {"jit": "off"}  # Disable JIT for better performance
    }
    if "postgresql+asyncpg" in DATABASE_URL
    else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_application_session():
    """
    Provides an application-level async database session.
    Usage: async with get_application_session() as session:
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


class DatabaseManager:
    """Database manager with session context management."""

    def __init__(self):
        self.engine = engine
        self.session_factory = AsyncSessionLocal

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database sessions with automatic commit/rollback."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def get_session_direct(self) -> AsyncSession:
        """Direct session creation (remember to close manually)."""
        return self.session_factory()

    async def close_engine(self):
        """Close engine when shutting down."""
        await self.engine.dispose()


# Global instance
db_manager = DatabaseManager()


# Legacy aliases for backward compatibility during migration
DatabaseSessionLocal = AsyncSessionLocal
database_engine = engine


async def get_maria_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Legacy alias for get_application_session.
    New code should use get_application_session() or db_manager.get_session().
    """
    async for session in get_application_session():
        yield session


async def create_tables():
    """
    Create database tables using SQLModel metadata.
    Legacy alias for backward compatibility.
    """
    from db.model import TableModel
    from sqlmodel import SQLModel

    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables created successfully")
