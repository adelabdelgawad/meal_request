"""
Pagination utilities for list endpoints.

Provides helpers for:
- Consistent pagination response format
- Offset/limit calculation
- Metadata generation
"""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMetadata(BaseModel):
    """Metadata for paginated responses."""

    total_count: int = Field(description="Total number of items across all pages")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    data: List[T] = Field(description="Items in this page")
    pagination: PaginationMetadata


def calculate_offset(page: int, page_size: int) -> int:
    """
    Calculate offset for SQL LIMIT/OFFSET clause.

    Args:
        page: 1-indexed page number
        page_size: Number of items per page

    Returns:
        Offset for query (0-indexed)

    Example:
        >>> calculate_offset(1, 10)
        0
        >>> calculate_offset(2, 10)
        10
        >>> calculate_offset(3, 10)
        20
    """
    if page < 1:
        page = 1
    return (page - 1) * page_size


def calculate_pagination_metadata(
    total_count: int,
    page: int,
    page_size: int,
) -> PaginationMetadata:
    """
    Generate pagination metadata for a response.

    Args:
        total_count: Total number of items
        page: Current 1-indexed page number
        page_size: Number of items per page

    Returns:
        PaginationMetadata with calculated values

    Example:
        >>> meta = calculate_pagination_metadata(100, 2, 10)
        >>> meta.total_pages
        10
        >>> meta.has_next
        True
        >>> meta.has_previous
        True
    """
    if page < 1:
        page = 1

    total_pages = (total_count + page_size - 1) // page_size
    if total_pages == 0:
        total_pages = 1

    return PaginationMetadata(
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )
