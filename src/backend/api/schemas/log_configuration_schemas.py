"""Log Configuration Schemas - Audit logging for configuration changes."""

from datetime import datetime
from typing import Optional

from api.schemas._base import CamelModel


class LogConfigurationCreate(CamelModel):
    """Schema for creating configuration audit log entries."""
    admin_id: str
    entity_type: str  # 'meal_type', 'department', 'page', etc.
    entity_id: Optional[str] = None
    action: str
    is_successful: bool
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    result: Optional[str] = None


class LogConfigurationResponse(CamelModel):
    """Schema for configuration audit log responses."""
    id: str
    timestamp: datetime
    admin_id: str
    entity_type: str
    entity_id: Optional[str]
    action: str
    is_successful: bool
    old_value: Optional[str]
    new_value: Optional[str]
    result: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LogConfigurationQuery(CamelModel):
    """Schema for querying configuration audit logs."""
    admin_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class LogConfigurationList(CamelModel):
    """Schema for paginated configuration audit log list."""
    items: list[LogConfigurationResponse]
    total: int
    page: int
    per_page: int
