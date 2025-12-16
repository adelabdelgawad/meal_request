"""
Repository utility functions.

Provides common utilities used across all repositories.
"""

from typing import Any, Tuple, List
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def execute_paginated_query(
    session: AsyncSession,
    query: Select,
    page: int = 1,
    per_page: int = 25,
) -> Tuple[List[Any], int]:
    """
    Execute a paginated query with optimized count.

    Args:
        session: Database session
        query: SQLAlchemy Select query
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Tuple of (items, total_count)

    Example:
        query = select(User).where(User.is_active == True)
        users, total = await execute_paginated_query(session, query, page=1, per_page=10)
    """
    from core.pagination import calculate_offset

    # Optimized count query - only counts rows without loading data
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Execute paginated data query
    offset = calculate_offset(page, per_page)
    result = await session.execute(query.offset(offset).limit(per_page))
    items = result.scalars().all()

    return items, total


async def count_query_results(session: AsyncSession, query: Select) -> int:
    """
    Count the number of results for a query without loading data.

    Args:
        session: Database session
        query: SQLAlchemy Select query

    Returns:
        Total count of matching rows

    Example:
        query = select(User).where(User.is_active == True)
        total_active_users = await count_query_results(session, query)
    """
    count_query = select(func.count()).select_from(query.subquery())
    result = await session.execute(count_query)
    return result.scalar() or 0
