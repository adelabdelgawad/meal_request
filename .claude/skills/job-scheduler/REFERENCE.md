# Job Scheduler Reference

Complete API and model documentation for the Job Scheduler system.

## Database Models

### ScheduledJob

Primary job definition table in `src/backend/db/models.py`.

```python
class ScheduledJob(Base):
    __tablename__ = "scheduled_job"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Task Reference
    task_function_id: Mapped[int] = mapped_column(
        ForeignKey("task_function.id"),
        nullable=False
    )
    job_type_id: Mapped[int] = mapped_column(
        ForeignKey("scheduler_job_type.id"),
        nullable=False
    )

    # Naming (optional overrides)
    name_en: Mapped[Optional[str]] = mapped_column(String(255))
    name_ar: Mapped[Optional[str]] = mapped_column(String(255))
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)

    # Interval Schedule (one or more can be set)
    interval_seconds: Mapped[Optional[int]]
    interval_minutes: Mapped[Optional[int]]
    interval_hours: Mapped[Optional[int]]
    interval_days: Mapped[Optional[int]]

    # Cron Schedule
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100))

    # Execution Settings
    priority: Mapped[int] = mapped_column(default=0)
    max_instances: Mapped[int] = mapped_column(default=1)
    misfire_grace_time: Mapped[int] = mapped_column(default=60)
    coalesce: Mapped[bool] = mapped_column(default=True)

    # Status Flags
    is_enabled: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_primary: Mapped[bool] = mapped_column(default=False)

    # Audit Fields
    last_run_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now())
    created_by_id: Mapped[Optional[str]] = mapped_column(String(36))
    updated_by_id: Mapped[Optional[str]] = mapped_column(String(36))

    # Relationships
    task_function: Mapped["TaskFunction"] = relationship()
    job_type: Mapped["SchedulerJobType"] = relationship()
    executions: Mapped[List["ScheduledJobExecution"]] = relationship(back_populates="job")
```

#### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `task_function_id` | int | FK to TaskFunction - defines what code runs |
| `job_type_id` | int | FK to SchedulerJobType (1=interval, 2=cron) |
| `interval_*` | int | Interval timing (at least one required for interval jobs) |
| `cron_expression` | str | Standard cron syntax (required for cron jobs) |
| `priority` | int | Execution order when multiple jobs ready (higher = first) |
| `max_instances` | int | Max parallel executions (1-10) |
| `misfire_grace_time` | int | Seconds to still run a missed job |
| `coalesce` | bool | If True, combine missed runs into one |
| `is_enabled` | bool | Whether job should be scheduled |
| `is_active` | bool | Soft delete flag (False = deleted) |
| `is_primary` | bool | Marks critical system jobs |

### ScheduledJobExecution

Tracks every job execution in `src/backend/db/models.py`.

```python
class ScheduledJobExecution(Base):
    __tablename__ = "scheduled_job_execution"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Job Reference
    job_id: Mapped[int] = mapped_column(
        ForeignKey("scheduled_job.id"),
        nullable=False
    )
    execution_id: Mapped[str] = mapped_column(String(36), unique=True)

    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    started_at: Mapped[Optional[datetime]]
    completed_at: Mapped[Optional[datetime]]
    duration_ms: Mapped[Optional[int]]

    # Outcome
    status_id: Mapped[int] = mapped_column(
        ForeignKey("scheduler_execution_status.id"),
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text)
    result_summary: Mapped[Optional[str]] = mapped_column(Text)

    # Context
    executor_id: Mapped[str] = mapped_column(String(36))
    host_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    # Relationships
    job: Mapped["ScheduledJob"] = relationship(back_populates="executions")
    status: Mapped["SchedulerExecutionStatus"] = relationship()
```

### ScheduledJobLock

Distributed locking for preventing duplicate execution.

```python
class ScheduledJobLock(Base):
    __tablename__ = "scheduled_job_lock"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("scheduled_job.id"))
    execution_id: Mapped[str] = mapped_column(String(36))
    locked_by: Mapped[str] = mapped_column(String(36))  # Instance ID
    locked_at: Mapped[datetime]
    expires_at: Mapped[datetime]  # Default: locked_at + 1 hour
```

### SchedulerInstance

Multi-instance coordination for embedded/standalone modes.

```python
class SchedulerInstance(Base):
    __tablename__ = "scheduler_instance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    instance_name: Mapped[str] = mapped_column(String(255))
    host_name: Mapped[str] = mapped_column(String(255))
    process_id: Mapped[int]
    mode: Mapped[str] = mapped_column(String(20))  # "embedded" or "standalone"
    status: Mapped[str] = mapped_column(String(20))  # starting/running/paused/stopped
    last_heartbeat: Mapped[datetime]
    started_at: Mapped[datetime]
    stopped_at: Mapped[Optional[datetime]]
```

### Lookup Tables

#### TaskFunction

Predefined task functions available for scheduling.

```python
class TaskFunction(Base):
    __tablename__ = "task_function"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)  # e.g., "hris_sync"
    name_en: Mapped[str] = mapped_column(String(255))
    name_ar: Mapped[str] = mapped_column(String(255))
    description_en: Mapped[Optional[str]] = mapped_column(Text)
    description_ar: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
```

#### SchedulerJobType

Job type enumeration (interval vs cron).

```python
class SchedulerJobType(Base):
    __tablename__ = "scheduler_job_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))  # "interval" or "cron"
    name_en: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str] = mapped_column(String(100))
```

#### SchedulerExecutionStatus

Execution status enumeration.

```python
class SchedulerExecutionStatus(Base):
    __tablename__ = "scheduler_execution_status"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))  # pending/running/success/failed
    name_en: Mapped[str] = mapped_column(String(100))
    name_ar: Mapped[str] = mapped_column(String(100))
```

---

## API Endpoints

All endpoints are in `src/backend/api/v1/scheduler.py` and require Super Admin authentication.

### Create Job

**POST** `/api/v1/scheduler/jobs`

Auto-detects job type from request body.

```json
// Request - Interval Job
{
  "taskFunctionId": 1,
  "nameEn": "HRIS Sync",
  "nameAr": "مزامنة الموارد البشرية",
  "intervalMinutes": 30,
  "priority": 5,
  "maxInstances": 1,
  "isEnabled": true
}

// Request - Cron Job
{
  "taskFunctionId": 2,
  "cronExpression": "0 2 * * *",
  "isEnabled": true
}

// Response
{
  "id": 1,
  "taskFunctionId": 1,
  "taskFunctionKey": "hris_sync",
  "jobTypeId": 1,
  "jobTypeName": "interval",
  "nameEn": "HRIS Sync",
  "intervalMinutes": 30,
  "priority": 5,
  "maxInstances": 1,
  "misfireGraceTime": 60,
  "coalesce": true,
  "isEnabled": true,
  "isActive": true,
  "createdAt": "2025-01-07T10:00:00Z"
}
```

### List Jobs

**GET** `/api/v1/scheduler/jobs`

Query parameters:
- `page` (int, default: 1)
- `per_page` (int, default: 20, max: 100)
- `is_enabled` (bool, optional)
- `job_type_id` (int, optional)

```json
// Response
{
  "items": [...],
  "total": 15,
  "page": 1,
  "perPage": 20,
  "totalPages": 1
}
```

### Get Job

**GET** `/api/v1/scheduler/jobs/{job_id}`

Returns full job details including next scheduled run.

### Update Job

**PUT** `/api/v1/scheduler/jobs/{job_id}`

```json
// Request
{
  "intervalMinutes": 60,
  "priority": 10,
  "isEnabled": false
}
```

### Delete Job

**DELETE** `/api/v1/scheduler/jobs/{job_id}`

Soft delete (sets `is_active = false`).

### Perform Job Action

**POST** `/api/v1/scheduler/jobs/{job_id}/action`

```json
// Request
{
  "action": "trigger"  // enable | disable | trigger | pause | resume
}

// Response
{
  "success": true,
  "message": "Job triggered successfully",
  "executionId": "uuid-here",  // Only for trigger action
  "job": {...}
}
```

#### Action Types

| Action | Description |
|--------|-------------|
| `enable` | Set `is_enabled = true`, reschedule job |
| `disable` | Set `is_enabled = false`, remove from scheduler |
| `trigger` | Execute immediately, returns `executionId` |
| `pause` | Temporarily suspend without disabling |
| `resume` | Resume after pause |

### Get Job History

**GET** `/api/v1/scheduler/jobs/{job_id}/history`

Query parameters:
- `page`, `per_page`
- `status_id` (int, optional)

```json
// Response
{
  "items": [
    {
      "id": 100,
      "jobId": 1,
      "executionId": "uuid",
      "scheduledAt": "2025-01-07T10:00:00Z",
      "startedAt": "2025-01-07T10:00:01Z",
      "completedAt": "2025-01-07T10:00:05Z",
      "durationMs": 4000,
      "statusId": 3,
      "statusName": "success",
      "resultSummary": "Synced 150 records"
    }
  ],
  "total": 50
}
```

### Get All History

**GET** `/api/v1/scheduler/history`

Same as job history but across all jobs.

### Get Scheduler Status

**GET** `/api/v1/scheduler/status`

```json
// Response
{
  "isRunning": true,
  "mode": "embedded",
  "instanceId": "uuid",
  "activeInstances": 1,
  "totalJobs": 15,
  "enabledJobs": 12,
  "runningExecutions": 2,
  "lastHeartbeat": "2025-01-07T10:30:00Z"
}
```

### Cleanup History

**POST** `/api/v1/scheduler/cleanup`

```json
// Request
{
  "retentionDays": 30  // Optional, default: 30
}

// Response
{
  "deletedCount": 1500,
  "message": "Cleaned up 1500 execution records older than 30 days"
}
```

### Get Task Functions

**GET** `/api/v1/scheduler/task-functions`

Returns list of available task functions for job creation.

### Get Job Types

**GET** `/api/v1/scheduler/job-types`

Returns `[{id: 1, name: "interval"}, {id: 2, name: "cron"}]`.

### Get Execution Statuses

**GET** `/api/v1/scheduler/execution-statuses`

Returns `[{id: 1, name: "pending"}, {id: 2, name: "running"}, ...]`.

---

## Service Layer

`src/backend/api/services/scheduler_service.py`

### Key Methods

```python
class SchedulerService:
    # Lifecycle
    async def initialize(session, mode="embedded", instance_name=None) -> str
    async def start(session) -> None
    async def stop(session, wait=True) -> None

    # Job CRUD
    async def create_job(session, data, created_by_id) -> ScheduledJob
    async def get_job(session, job_id) -> ScheduledJobResponse
    async def list_jobs(session, page, per_page, filters) -> Tuple[List, int]
    async def update_job(session, job_id, data, updated_by_id) -> ScheduledJob
    async def delete_job(session, job_id) -> ScheduledJob

    # Actions
    async def enable_job(session, job_id) -> ScheduledJob
    async def disable_job(session, job_id) -> ScheduledJob
    async def trigger_job_now(session, job_id, triggered_by_user_id) -> Tuple[str, ScheduledJob]
    async def pause_job(session, job_id) -> ScheduledJob
    async def resume_job(session, job_id) -> ScheduledJob

    # History
    async def get_job_history(session, job_id, filters, page, per_page) -> Tuple[List, int]
    async def get_all_history(session, filters, page, per_page) -> Tuple[List, int]

    # Status
    async def get_status(session) -> SchedulerStatusResponse
    async def cleanup_history(session, retention_days=30) -> dict
```

---

## Repository Layer

`src/backend/api/repositories/scheduler_repository.py`

### Key Methods

```python
class SchedulerRepository:
    # Jobs
    async def create_job(session, job_data) -> ScheduledJob
    async def get_job_by_id(session, job_id) -> Optional[ScheduledJob]
    async def get_jobs(session, filters, page, per_page) -> Tuple[List, int]
    async def update_job(session, job_id, update_data) -> ScheduledJob
    async def soft_delete_job(session, job_id) -> ScheduledJob

    # Executions
    async def create_execution(session, exec_data) -> ScheduledJobExecution
    async def update_execution(session, execution_id, update_data) -> ScheduledJobExecution
    async def get_executions(session, job_id, filters, page, per_page) -> Tuple[List, int]

    # Locks
    async def acquire_lock(session, job_id, execution_id, instance_id) -> bool
    async def release_lock(session, job_id, execution_id) -> None
    async def check_lock(session, job_id) -> Optional[ScheduledJobLock]

    # Instances
    async def register_instance(session, instance_data) -> SchedulerInstance
    async def update_heartbeat(session, instance_id) -> None
    async def get_active_instances(session) -> List[SchedulerInstance]

    # Lookups
    async def get_task_functions(session) -> List[TaskFunction]
    async def get_job_types(session) -> List[SchedulerJobType]
    async def get_execution_statuses(session) -> List[SchedulerExecutionStatus]
```

---

## Schemas

`src/backend/api/schemas/scheduler_schemas.py`

All schemas inherit from `CamelModel` for automatic camelCase JSON serialization.

### Request Schemas

```python
class ScheduledJobCreate(CamelModel):
    task_function_id: int
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None

    # Interval (optional)
    interval_seconds: Optional[int] = None
    interval_minutes: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_days: Optional[int] = None

    # Cron (optional)
    cron_expression: Optional[str] = None

    # Settings
    priority: int = 0
    max_instances: int = Field(default=1, ge=1, le=10)
    misfire_grace_time: int = 60
    coalesce: bool = True
    is_enabled: bool = True

class ScheduledJobUpdate(CamelModel):
    # All fields optional for partial updates
    name_en: Optional[str] = None
    interval_minutes: Optional[int] = None
    cron_expression: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None
    # ... etc

class JobActionRequest(CamelModel):
    action: Literal["enable", "disable", "trigger", "pause", "resume"]
```

### Response Schemas

```python
class ScheduledJobResponse(CamelModel):
    id: int
    task_function_id: int
    task_function_key: str
    job_type_id: int
    job_type_name: str
    name_en: Optional[str]
    name_ar: Optional[str]
    # ... all job fields
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]

class ScheduledJobExecutionResponse(CamelModel):
    id: int
    job_id: int
    execution_id: str
    scheduled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    status_id: int
    status_name: str
    error_message: Optional[str]
    result_summary: Optional[str]

class JobActionResponse(CamelModel):
    success: bool
    message: str
    execution_id: Optional[str] = None  # For trigger action
    job: ScheduledJobResponse

class SchedulerStatusResponse(CamelModel):
    is_running: bool
    mode: str
    instance_id: str
    active_instances: int
    total_jobs: int
    enabled_jobs: int
    running_executions: int
    last_heartbeat: datetime
```

---

## TypeScript Types

`src/my-app/types/scheduler.ts`

```typescript
export interface ScheduledJob {
  id: number;
  taskFunctionId: number;
  taskFunctionKey: string;
  jobTypeId: number;
  jobTypeName: string;
  nameEn?: string;
  nameAr?: string;
  descriptionEn?: string;
  descriptionAr?: string;
  cronExpression?: string;
  intervalSeconds?: number;
  intervalMinutes?: number;
  intervalHours?: number;
  intervalDays?: number;
  priority: number;
  maxInstances: number;
  misfireGraceTime: number;
  coalesce: boolean;
  isEnabled: boolean;
  isActive: boolean;
  isPrimary: boolean;
  lastRunAt?: string;
  nextRunAt?: string;
  createdAt: string;
  updatedAt?: string;
}

export interface ScheduledJobExecution {
  id: number;
  jobId: number;
  executionId: string;
  scheduledAt: string;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  statusId: number;
  statusName: string;
  errorMessage?: string;
  resultSummary?: string;
  executorId: string;
  hostName: string;
}

export type JobAction = 'enable' | 'disable' | 'trigger' | 'pause' | 'resume';

export interface JobActionRequest {
  action: JobAction;
}

export interface JobActionResponse {
  success: boolean;
  message: string;
  executionId?: string;
  job: ScheduledJob;
}

export interface SchedulerStatus {
  isRunning: boolean;
  mode: string;
  instanceId: string;
  activeInstances: number;
  totalJobs: number;
  enabledJobs: number;
  runningExecutions: number;
  lastHeartbeat: string;
}
```
