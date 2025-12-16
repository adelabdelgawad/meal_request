"""
User Management Audit Log Schemas - Stream 4

Schemas for tracking user CRUD operations.
Actions: create, update_profile, update_status, delete, password_change, role_assignment
"""

from typing import Optional
from datetime import datetime

from api.schemas._base import CamelModel


class LogUserCreate(CamelModel):
    """Schema for creating a user management audit log entry."""
    admin_id: str
    target_user_id: Optional[str] = None
    action: str
    is_successful: bool
    old_value: Optional[str] = None  # JSON string
    new_value: Optional[str] = None  # JSON string
    result: Optional[str] = None  # JSON string


class LogUserResponse(CamelModel):
    """Schema for user management audit log response."""
    id: str
    timestamp: datetime
    admin_id: str
    target_user_id: Optional[str]
    action: str
    is_successful: bool
    old_value: Optional[str]
    new_value: Optional[str]
    result: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LogUserQuery(CamelModel):
    """Schema for querying user management audit logs."""
    admin_id: Optional[str] = None
    target_user_id: Optional[str] = None
    action: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class LogUserList(CamelModel):
    """Schema for paginated user management audit log list."""
    items: list[LogUserResponse]
    total: int
    page: int
    per_page: int
