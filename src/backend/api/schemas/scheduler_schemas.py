"""
Pydantic schemas for scheduler management.

All schemas inherit from CamelModel for automatic camelCase JSON serialization.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator

from api.schemas._base import CamelModel


# Enums for instance modes and statuses
class InstanceMode(str, Enum):
    EMBEDDED = "embedded"
    STANDALONE = "standalone"


class InstanceStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


class JobAction(str, Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    TRIGGER = "trigger"
    PAUSE = "pause"
    RESUME = "resume"


# -------------------
# Lookup Table Response Schemas
# -------------------


class TaskFunctionResponse(CamelModel):
    """Response schema for a task function."""

    id: int
    key: str
    function_path: str
    name_en: str
    name_ar: str
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    is_active: bool


class TaskFunctionListResponse(CamelModel):
    """Response schema for list of task functions."""

    items: List[TaskFunctionResponse]
    total: int


class SchedulerJobTypeResponse(CamelModel):
    """Response schema for a scheduler job type."""

    id: int
    code: str
    name_en: str
    name_ar: str
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    sort_order: int
    is_active: bool


class SchedulerJobTypeListResponse(CamelModel):
    """Response schema for list of scheduler job types."""

    items: List[SchedulerJobTypeResponse]
    total: int


class SchedulerExecutionStatusResponse(CamelModel):
    """Response schema for a scheduler execution status."""

    id: int
    code: str
    name_en: str
    name_ar: str
    sort_order: int
    is_active: bool


class SchedulerExecutionStatusListResponse(CamelModel):
    """Response schema for list of scheduler execution statuses."""

    items: List[SchedulerExecutionStatusResponse]
    total: int


# -------------------
# Job Creation Schemas
# -------------------


class ScheduledJobIntervalCreate(CamelModel):
    """Schema for creating an interval-based scheduled job."""

    task_function_id: int = Field(
        ..., description="ID of the task function to schedule"
    )
    name_en: Optional[str] = Field(
        None,
        max_length=128,
        description="English job name (overrides task function)",
    )
    name_ar: Optional[str] = Field(
        None,
        max_length=128,
        description="Arabic job name (overrides task function)",
    )
    description_en: Optional[str] = Field(
        None, max_length=512, description="English description"
    )
    description_ar: Optional[str] = Field(
        None, max_length=512, description="Arabic description"
    )
    # Interval fields - at least one must be provided
    interval_seconds: Optional[int] = Field(
        None, ge=1, description="Run every N seconds"
    )
    interval_minutes: Optional[int] = Field(
        None, ge=1, description="Run every N minutes"
    )
    interval_hours: Optional[int] = Field(
        None, ge=1, description="Run every N hours"
    )
    interval_days: Optional[int] = Field(
        None, ge=1, description="Run every N days"
    )
    # Execution settings
    priority: int = Field(0, ge=0, description="Higher = runs first")
    max_instances: int = Field(
        1, ge=1, le=10, description="Max concurrent executions"
    )
    misfire_grace_time: int = Field(
        300, ge=0, description="Grace time in seconds"
    )
    coalesce: bool = Field(True, description="Combine missed runs")
    is_enabled: bool = Field(True, description="Enable job on creation")
    is_primary: bool = Field(False, description="Mark as primary job")

    @field_validator("interval_days", mode="after")
    @classmethod
    def validate_at_least_one_interval(cls, v, info):
        """Ensure at least one interval field is provided."""
        values = info.data
        if not any(
            [
                values.get("interval_seconds"),
                values.get("interval_minutes"),
                values.get("interval_hours"),
                v,
            ]
        ):
            raise ValueError("At least one interval field must be provided")
        return v


class ScheduledJobCronCreate(CamelModel):
    """Schema for creating a cron-based scheduled job."""

    task_function_id: int = Field(
        ..., description="ID of the task function to schedule"
    )
    name_en: Optional[str] = Field(
        None,
        max_length=128,
        description="English job name (overrides task function)",
    )
    name_ar: Optional[str] = Field(
        None,
        max_length=128,
        description="Arabic job name (overrides task function)",
    )
    description_en: Optional[str] = Field(
        None, max_length=512, description="English description"
    )
    description_ar: Optional[str] = Field(
        None, max_length=512, description="Arabic description"
    )
    cron_expression: str = Field(
        ..., min_length=1, max_length=64, description="Cron expression"
    )
    # Execution settings
    priority: int = Field(0, ge=0, description="Higher = runs first")
    max_instances: int = Field(
        1, ge=1, le=10, description="Max concurrent executions"
    )
    misfire_grace_time: int = Field(
        300, ge=0, description="Grace time in seconds"
    )
    coalesce: bool = Field(True, description="Combine missed runs")
    is_enabled: bool = Field(True, description="Enable job on creation")
    is_primary: bool = Field(False, description="Mark as primary job")


class ScheduledJobCreate(CamelModel):
    """Unified schema for creating a scheduled job."""

    task_function_id: int = Field(
        ..., description="ID of the task function to schedule"
    )
    job_type_id: int = Field(
        ..., description="ID of the job type (interval or cron)"
    )
    name_en: Optional[str] = Field(
        None,
        max_length=128,
        description="English job name (overrides task function)",
    )
    name_ar: Optional[str] = Field(
        None,
        max_length=128,
        description="Arabic job name (overrides task function)",
    )
    description_en: Optional[str] = Field(
        None, max_length=512, description="English description"
    )
    description_ar: Optional[str] = Field(
        None, max_length=512, description="Arabic description"
    )
    # Interval fields - required when job_type is interval
    interval_seconds: Optional[int] = Field(
        None, ge=1, description="Run every N seconds"
    )
    interval_minutes: Optional[int] = Field(
        None, ge=1, description="Run every N minutes"
    )
    interval_hours: Optional[int] = Field(
        None, ge=1, description="Run every N hours"
    )
    interval_days: Optional[int] = Field(
        None, ge=1, description="Run every N days"
    )
    # Cron field - required when job_type is cron
    cron_expression: Optional[str] = Field(
        None, max_length=64, description="Cron expression"
    )
    # Execution settings
    priority: int = Field(0, ge=0, description="Higher = runs first")
    max_instances: int = Field(
        1, ge=1, le=10, description="Max concurrent executions"
    )
    misfire_grace_time: int = Field(
        300, ge=0, description="Grace time in seconds"
    )
    coalesce: bool = Field(True, description="Combine missed runs")
    is_enabled: bool = Field(True, description="Enable job on creation")
    is_primary: bool = Field(False, description="Mark as primary job")


# -------------------
# Job Update Schema
# -------------------


class ScheduledJobUpdate(CamelModel):
    """Schema for updating an existing scheduled job."""

    task_function_id: Optional[int] = Field(
        None, description="ID of the task function"
    )
    job_type_id: Optional[int] = Field(None, description="ID of the job type")
    name_en: Optional[str] = Field(None, max_length=128)
    name_ar: Optional[str] = Field(None, max_length=128)
    description_en: Optional[str] = Field(None, max_length=512)
    description_ar: Optional[str] = Field(None, max_length=512)
    interval_seconds: Optional[int] = Field(None, ge=1)
    interval_minutes: Optional[int] = Field(None, ge=1)
    interval_hours: Optional[int] = Field(None, ge=1)
    interval_days: Optional[int] = Field(None, ge=1)
    cron_expression: Optional[str] = Field(None, max_length=64)
    priority: Optional[int] = Field(None, ge=0)
    max_instances: Optional[int] = Field(None, ge=1, le=10)
    misfire_grace_time: Optional[int] = Field(None, ge=0)
    coalesce: Optional[bool] = None
    is_enabled: Optional[bool] = None
    is_primary: Optional[bool] = None


# -------------------
# Job Response Schemas
# -------------------


class ScheduledJobResponse(CamelModel):
    """Response schema for a scheduled job."""

    id: int
    task_function_id: int
    job_type_id: int
    # Computed from task_function for backward compatibility
    job_key: str
    job_function: str
    job_type: str
    # Names (from job or task_function)
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    # Schedule settings
    interval_seconds: Optional[int] = None
    interval_minutes: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_days: Optional[int] = None
    cron_expression: Optional[str] = None
    # Execution settings
    priority: int
    max_instances: int
    misfire_grace_time: int
    coalesce: bool
    # Status
    is_enabled: bool
    is_active: bool
    is_primary: bool = False
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None  # Last time job was triggered
    created_by_id: Optional[str] = None
    updated_by_id: Optional[str] = None
    # Nested objects
    task_function: Optional[TaskFunctionResponse] = None
    job_type_ref: Optional[SchedulerJobTypeResponse] = None
    # Computed fields (added by service)
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    last_run_status: Optional[str] = None
    # Current execution status (pending/running)
    current_execution_status: Optional[str] = (
        None  # "pending", "running", or None
    )
    current_execution_id: Optional[str] = (
        None  # UUID of current pending/running execution
    )


class ScheduledJobListResponse(CamelModel):
    """Paginated response for scheduled jobs list."""

    items: List[ScheduledJobResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# -------------------
# Execution Response Schemas
# -------------------


class JobExecutionResponse(CamelModel):
    """Response schema for a job execution record."""

    id: int
    job_id: int
    execution_id: str
    run_id: Optional[str] = None
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    status_id: int
    # Computed from status_ref for backward compatibility
    status: str
    status_name_en: Optional[str] = None
    status_name_ar: Optional[str] = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    result_summary: Optional[str] = None
    executor_id: Optional[str] = None
    host_name: Optional[str] = None
    created_at: datetime
    # Nested object
    status_ref: Optional[SchedulerExecutionStatusResponse] = None


class JobExecutionListResponse(CamelModel):
    """Paginated response for job execution history."""

    items: List[JobExecutionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# -------------------
# Action Schemas
# -------------------


class JobActionRequest(CamelModel):
    """Request schema for job actions."""

    action: JobAction


class JobActionResponse(CamelModel):
    """Response schema for job actions."""

    success: bool
    message: str
    job_id: str
    action: str
    execution_id: Optional[str] = None  # UUID for trigger action
    job: Optional["ScheduledJobResponse"] = (
        None  # Updated job data (for trigger action)
    )


# -------------------
# Status Schemas
# -------------------


class SchedulerInstanceResponse(CamelModel):
    """Response schema for a scheduler instance."""

    id: str
    instance_name: str
    host_name: str
    process_id: int
    mode: str
    status: str
    last_heartbeat: datetime
    started_at: datetime
    stopped_at: Optional[datetime] = None


class SchedulerStatusResponse(CamelModel):
    """Response schema for overall scheduler status."""

    is_running: bool
    total_jobs: int
    enabled_jobs: int
    disabled_jobs: int
    active_instances: List[SchedulerInstanceResponse]
    next_scheduled_job: Optional[ScheduledJobResponse] = None
    recent_executions: List[JobExecutionResponse] = []


# -------------------
# Cleanup Schema
# -------------------


class CleanupRequest(CamelModel):
    """Request schema for cleanup operation."""

    retention_days: int = Field(30, ge=1, le=365, description="Days to retain")


class CleanupResponse(CamelModel):
    """Response schema for cleanup operation."""

    success: bool
    deleted_executions: int
    deleted_locks: int
    deleted_instances: int
    message: str
