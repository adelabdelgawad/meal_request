"""
DomainUser Schemas - Pydantic DTOs for DomainUser entity.

Schemas for caching and managing Active Directory user information.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from api.schemas._base import CamelModel


class DomainUserBase(CamelModel):
    """Base schema for DomainUser with common fields."""

    username: str = Field(min_length=1, max_length=64, description="AD username")
    email: Optional[str] = Field(None, max_length=128, description="Email address from AD")
    full_name: Optional[str] = Field(None, max_length=128, description="Full name from AD")
    title: Optional[str] = Field(None, max_length=128, description="Job title from AD")
    office: Optional[str] = Field(None, max_length=128, description="Office location")
    phone: Optional[str] = Field(None, max_length=32, description="Phone number")
    manager: Optional[str] = Field(None, max_length=128, description="Manager's name or username")


class DomainUserCreate(DomainUserBase):
    """Schema for creating a new DomainUser."""

    pass


class DomainUserUpdate(CamelModel):
    """Schema for updating an existing DomainUser."""

    email: Optional[str] = Field(None, max_length=128)
    full_name: Optional[str] = Field(None, max_length=128)
    title: Optional[str] = Field(None, max_length=128)
    office: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    manager: Optional[str] = Field(None, max_length=128)


class DomainUserResponse(DomainUserBase):
    """Schema for returning DomainUser data in API responses."""

    id: int
    created_at: datetime
    updated_at: datetime


class DomainUserListResponse(CamelModel):
    """Schema for paginated DomainUser list response."""

    items: list[DomainUserResponse]
    total: int
    page: int = Field(default=1, description="Current page number")
    limit: int = Field(default=50, description="Items per page")
    has_more: bool = Field(default=False, description="Whether there are more results")


class DomainUserSyncResponse(CamelModel):
    """Schema for AD sync operation response."""

    deleted_count: int = Field(description="Number of records deleted from the table")
    created_count: int = Field(description="Number of records created from AD")
    ad_users_fetched: int = Field(description="Number of users fetched from Active Directory")
