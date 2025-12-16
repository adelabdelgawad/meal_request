"""Log Role Schemas - Audit logging for role management."""

from datetime import datetime
from typing import Optional

from api.schemas._base import CamelModel


class LogRoleCreate(CamelModel):
    """Schema for creating role audit log entries."""
    admin_id: str
    role_id: Optional[int] = None
    action: str
    is_successful: bool
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    result: Optional[str] = None


class LogRoleResponse(CamelModel):
    """Schema for role audit log responses."""
    id: str
    timestamp: datetime
    admin_id: str
    role_id: Optional[int]
    action: str
    is_successful: bool
    old_value: Optional[str]
    new_value: Optional[str]
    result: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LogRoleQuery(CamelModel):
    """Schema for querying role audit logs."""
    admin_id: Optional[str] = None
    role_id: Optional[int] = None
    action: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class LogRoleList(CamelModel):
    """Schema for paginated role audit log list."""
    items: list[LogRoleResponse]
    total: int
    page: int
    per_page: int
