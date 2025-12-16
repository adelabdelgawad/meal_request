"""Log Meal Request Schemas - Audit logging for meal request operations."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class LogMealRequestBase(CamelModel):
    """Base schema for meal request audit logs."""
    user_id: str
    meal_request_id: Optional[int] = None
    action: str
    is_successful: bool
    old_value: Optional[str] = None  # JSON string
    new_value: Optional[str] = None  # JSON string
    result: Optional[str] = None  # JSON string

    model_config = ConfigDict(from_attributes=True)


class LogMealRequestCreate(LogMealRequestBase):
    """Schema for creating a meal request audit log entry."""
    pass


class LogMealRequestResponse(LogMealRequestBase):
    """Schema for meal request audit log response."""
    id: str
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LogMealRequestQuery(CamelModel):
    """Schema for querying meal request audit logs."""
    user_id: Optional[str] = None
    meal_request_id: Optional[int] = None
    action: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LogMealRequestList(CamelModel):
    """Schema for paginated meal request audit log list."""
    items: list[LogMealRequestResponse]
    total: int
    page: int
    per_page: int

    model_config = ConfigDict(from_attributes=True)
