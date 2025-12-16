"""Log Permission Schemas."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict

from api.schemas._base import CamelModel


class LogPermissionBase(CamelModel):
    user_id: str
    role_id: int
    admin_id: str
    action: str
    is_successful: bool
    result: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LogPermissionCreate(LogPermissionBase):
    pass


class LogPermissionResponse(LogPermissionBase):
    id: int
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
