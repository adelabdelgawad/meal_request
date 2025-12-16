"""Schemas for replication audit logs."""

from datetime import datetime
from typing import Optional

from api.schemas._base import CamelModel


class LogReplicationBase(CamelModel):
    """Base schema for replication logs."""

    operation_type: str
    is_successful: bool
    admin_id: Optional[str] = None
    records_processed: Optional[int] = None
    records_created: Optional[int] = None
    records_updated: Optional[int] = None
    records_skipped: Optional[int] = None
    records_failed: Optional[int] = None
    source_system: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    result: Optional[str] = None  # JSON string


class LogReplicationCreate(LogReplicationBase):
    """Schema for creating a replication log."""

    pass


class LogReplicationResponse(LogReplicationBase):
    """Schema for replication log response."""

    id: str
    timestamp: datetime
    created_at: datetime
