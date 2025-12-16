import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base
from settings import settings

# Load environment variables from the .env file
load_dotenv()

# Extracting database details from settings or environment variables
if settings.MARIA_URL:
    # Use full DSN from settings
    DATABASE_URL = settings.MARIA_URL
    # Extract parts for server connection
    # Simple parsing - could be more robust
    parts = DATABASE_URL.replace("mysql+aiomysql://", "").split("@")
    if len(parts) == 2:
        user_pass = parts[0].split(":")
        server_db = parts[1].split("/")
        DB_USER = user_pass[0] if len(user_pass) > 0 else ""
        DB_PASSWORD = user_pass[1] if len(user_pass) > 1 else ""
        server_db_parts = server_db[0].split(":")
        DB_SERVER = server_db_parts[0] if len(server_db_parts) > 0 else ""
        DB_NAME = server_db[1].split("?")[0] if len(server_db) > 1 else ""  # Strip query parameters
    else:
        # Fallback to individual env vars if parsing fails
        DB_USER = os.getenv("APP_DB_USER", "")
        DB_PASSWORD = os.getenv("APP_DB_PASSWORD", "")
        DB_SERVER = os.getenv("APP_DB_SERVER", "")
        DB_NAME = os.getenv("APP_DB_NAME", "")
else:
    # Fallback to individual environment variables
    DB_USER = os.getenv("APP_DB_USER")
    DB_PASSWORD = os.getenv("APP_DB_PASSWORD")
    DB_SERVER = os.getenv("APP_DB_SERVER")
    DB_NAME = os.getenv("APP_DB_NAME")

    # Validate environment variables when using individual vars
    required_vars = [
        "APP_DB_USER",
        "APP_DB_PASSWORD",
        "APP_DB_SERVER",
        "APP_DB_NAME",
    ]
    missing_vars = [var for var in required_vars if os.getenv(var) is None]
    if missing_vars:
        raise EnvironmentError(
            f"Missing environment variables: {
                               ', '.join(missing_vars)}"
        )

    # URL for connecting to the specific database
    DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}?charset=utf8mb4"

# URL for connecting to the database server (not a specific database)
SERVER_DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/?charset=utf8mb4"
)

# Create the SQLAlchemy engines at the module level
server_engine = create_async_engine(SERVER_DATABASE_URL, echo=False)


# Create sessionmakers at the module level
ServerSessionLocal = async_sessionmaker(
    bind=server_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

database_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,      # Verify connections before use (detect stale connections)
    pool_recycle=3600,        # Recycle connections hourly (prevent event loop binding)
    pool_size=10,             # Base pool size
    max_overflow=20,          # Additional connections when needed
)
DatabaseSessionLocal = async_sessionmaker(
    bind=database_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_tables():
    """
    Creates the database if it doesn't exist and initializes tables based on SQLAlchemy models.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Step 1: Create the database with utf8mb4 character set if it doesn't exist
    logger.info(f"Creating database if not exists: {DB_NAME}")
    async with server_engine.begin() as conn:
        await conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{
                    DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
    logger.info(f"Database '{DB_NAME}' is ready")

    # Dispose server engine after database creation (no longer needed)
    await server_engine.dispose()

    # Step 2: Create tables in the specified database
    logger.info("Creating database tables...")
    async with database_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")

    # Note: database_engine is kept alive for application use
    # It will be disposed during application shutdown


async def get_maria_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous generator that yields a database session.
    Automatically commits on success, rolls back on error.
    Ensures the session is properly closed after use.
    Note: Engine disposal should happen at application shutdown, not per-request.
    """
    async with DatabaseSessionLocal() as session:
        try:
            yield session
            # Commit the transaction if no exception occurred
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Example usage: Creating tables when the module is run directly
if __name__ == "__main__":
    import asyncio

    async def main():
        await create_tables()

    asyncio.run(main())
