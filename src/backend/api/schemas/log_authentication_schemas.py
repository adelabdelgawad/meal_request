"""Log Authentication Schemas - Authentication audit log DTOs."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class LogAuthenticationBase(CamelModel):
    """Base schema for authentication logs."""
    user_id: Optional[str] = None
    action: str
    is_successful: bool
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    result: Optional[str] = None  # JSON string

    model_config = ConfigDict(from_attributes=True)


class LogAuthenticationCreate(LogAuthenticationBase):
    """Schema for creating authentication logs."""
    pass


class LogAuthenticationResponse(LogAuthenticationBase):
    """Schema for authentication log responses."""
    id: str
    timestamp: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LogAuthenticationQuery(CamelModel):
    """Schema for querying authentication logs."""
    user_id: Optional[str] = None
    action: Optional[str] = None
    is_successful: Optional[bool] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LogAuthenticationList(CamelModel):
    """Schema for paginated authentication log list."""
    items: list[LogAuthenticationResponse]
    total: int
    page: int
    per_page: int

    model_config = ConfigDict(from_attributes=True)
