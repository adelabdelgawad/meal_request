import os
import urllib
from typing import AsyncGenerator
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv
from core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables from the .env file
load_dotenv()


def convert_pyodbc_to_aioodbc(url: str) -> str:
    """
    Convert mssql+pyodbc URL to mssql+aioodbc format for async support.
    """
    if not url:
        return url

    # If already using aioodbc, return as-is
    if "aioodbc" in url:
        return url

    # Parse the URL to extract components
    parsed = urlparse(url)

    # Extract driver from query string
    query_params = parse_qs(parsed.query)
    driver = query_params.get("driver", ["ODBC Driver 17 for SQL Server"])[0]

    # Decode username and password (they may be URL-encoded)
    username = unquote(parsed.username) if parsed.username else ""
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname or ""
    database = parsed.path.lstrip("/") if parsed.path else ""

    # Build ODBC connection string
    odbc_params = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
    )

    # URL-encode the connection parameters for aioodbc
    encoded_params = urllib.parse.quote_plus(odbc_params)

    return f"mssql+aioodbc:///?odbc_connect={encoded_params}"


if settings.database.hris_url:
    # Convert pyodbc URL to aioodbc for async support
    SQL_DSN = convert_pyodbc_to_aioodbc(settings.database.hris_url)
else:
    # Fallback to individual environment variables
    DRIVER = os.getenv("HRIS_DB_DRIVER", "ODBC Driver 17 for SQL Server")
    SERVER = os.getenv("HRIS_DB_SERVER")
    DATABASE = os.getenv("HRIS_DB_NAME")
    USERNAME = os.getenv("HRIS_DB_USER")
    PASSWORD = os.getenv("HRIS_DB_PASSWORD")

    odbc_params = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
    )

    # URL-encode the connection parameters for aioodbc
    encoded_params = urllib.parse.quote_plus(odbc_params)
    SQL_DSN = f"mssql+aioodbc:///?odbc_connect={encoded_params}"


# Global engine and sessionmaker to avoid creating new engines per request
_HRIS_ENGINE = None
_HRIS_SESSION_MAKER = None


def _get_hris_engine():
    """
    Get or create the HRIS engine (singleton pattern).

    Connection pool settings prevent event loop issues:
    - pool_pre_ping: Verify connections before use (detect stale connections)
    - pool_recycle: Recycle connections every hour (prevent event loop binding)
    - pool_size: Base connection pool size
    - max_overflow: Additional connections when pool exhausted
    """
    global _HRIS_ENGINE
    if _HRIS_ENGINE is None:
        _HRIS_ENGINE = create_async_engine(
            SQL_DSN,
            echo=False,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections hourly (1 hour)
            pool_size=5,  # Base pool size
            max_overflow=10,  # Additional connections when needed
        )
    return _HRIS_ENGINE


def _get_hris_session_maker():
    """Get or create the HRIS sessionmaker (singleton pattern)."""
    global _HRIS_SESSION_MAKER
    if _HRIS_SESSION_MAKER is None:
        engine = _get_hris_engine()
        _HRIS_SESSION_MAKER = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
    return _HRIS_SESSION_MAKER


async def get_hris_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous generator that yields a database session.
    Uses singleton pattern to avoid creating multiple engines.
    """
    AsyncSessionLocal = _get_hris_session_maker()

    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def dispose_hris_engine():
    """Dispose of the HRIS engine (call on application shutdown)."""
    global _HRIS_ENGINE, _HRIS_SESSION_MAKER
    if _HRIS_ENGINE is not None:
        await _HRIS_ENGINE.dispose()
        _HRIS_ENGINE = None
    _HRIS_SESSION_MAKER = None


# ============================================================================
# SYNCHRONOUS HRIS SESSIONS FOR CELERY TASKS
# ============================================================================


def _convert_aioodbc_to_pyodbc(aioodbc_url: str) -> str:
    """Convert aioodbc URL back to pyodbc for synchronous operations."""
    # aioodbc URLs are complex, extract the ODBC connection string
    if "odbc_connect=" in aioodbc_url:
        # Parse the encoded connection string
        import urllib.parse

        query_part = aioodbc_url.split("odbc_connect=")[1]
        odbc_string = urllib.parse.unquote_plus(query_part)
        # Build pyodbc DSN from ODBC connection string
        return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_string)}"
    return aioodbc_url


_SYNC_HRIS_ENGINE = None
_SYNC_HRIS_SESSION_MAKER = None


def _get_sync_hris_engine():
    """Get or create the synchronous HRIS engine for Celery tasks."""
    global _SYNC_HRIS_ENGINE
    if _SYNC_HRIS_ENGINE is None:
        # Convert aioodbc URL to pyodbc for sync operations
        sync_dsn = _convert_aioodbc_to_pyodbc(SQL_DSN)
        _SYNC_HRIS_ENGINE = create_engine(
            sync_dsn, echo=False, pool_size=5, max_overflow=10
        )
    return _SYNC_HRIS_ENGINE


def _get_sync_hris_session_maker():
    """Get or create the synchronous HRIS sessionmaker for Celery tasks."""
    global _SYNC_HRIS_SESSION_MAKER
    if _SYNC_HRIS_SESSION_MAKER is None:
        engine = _get_sync_hris_engine()
        _SYNC_HRIS_SESSION_MAKER = sessionmaker(
            bind=engine, class_=Session, expire_on_commit=False
        )
    return _SYNC_HRIS_SESSION_MAKER


def get_sync_hris_session() -> Session:
    """
    Get a synchronous HRIS database session for Celery tasks.

    Usage:
        session = get_sync_hris_session()
        try:
            # Do work
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    """
    SessionMaker = _get_sync_hris_session_maker()
    return SessionMaker()
