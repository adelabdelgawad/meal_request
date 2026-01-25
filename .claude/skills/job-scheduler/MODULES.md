# Job Scheduler Module Inventory

Complete inventory of all scheduler-related modules, files, and their responsibilities.

## Backend Modules

### API Layer

#### `src/backend/api/v1/scheduler.py`

**Purpose**: REST API endpoints for scheduler operations.

**Key Exports**:
- `router` - FastAPI APIRouter instance

**Endpoints Defined**:
| Function | Method | Path | Description |
|----------|--------|------|-------------|
| `create_job` | POST | `/jobs` | Create job (auto-detect type) |
| `create_interval_job` | POST | `/jobs/interval` | Create interval job |
| `create_cron_job` | POST | `/jobs/cron` | Create cron job |
| `list_jobs` | GET | `/jobs` | List jobs with pagination |
| `get_job` | GET | `/jobs/{job_id}` | Get single job |
| `update_job` | PUT | `/jobs/{job_id}` | Update job |
| `delete_job` | DELETE | `/jobs/{job_id}` | Soft delete job |
| `perform_job_action` | POST | `/jobs/{job_id}/action` | Execute action |
| `get_job_history` | GET | `/jobs/{job_id}/history` | Job execution history |
| `get_all_history` | GET | `/history` | All execution history |
| `get_scheduler_status` | GET | `/status` | Scheduler status |
| `cleanup_history` | POST | `/cleanup` | Clean old records |
| `get_task_functions` | GET | `/task-functions` | Available tasks |
| `get_job_types` | GET | `/job-types` | Job types |
| `get_execution_statuses` | GET | `/execution-statuses` | Status enum |

**Dependencies**:
- `api.services.scheduler_service`
- `api.schemas.scheduler_schemas`
- `db.maria_database`
- `utils.auth`

---

### Service Layer

#### `src/backend/api/services/scheduler_service.py`

**Purpose**: Business logic and APScheduler orchestration.

**Key Exports**:
- `scheduler_service` - Singleton instance of `SchedulerService`
- `SchedulerService` - Main service class

**Class: SchedulerService**

| Method | Description |
|--------|-------------|
| `initialize(session, mode, instance_name)` | Initialize scheduler instance |
| `start(session)` | Start the APScheduler |
| `stop(session, wait)` | Stop the APScheduler |
| `create_job(session, data, created_by_id)` | Create any job type |
| `create_interval_job(session, data, created_by_id)` | Create interval job |
| `create_cron_job(session, data, created_by_id)` | Create cron job |
| `get_job(session, job_id)` | Get job with computed fields |
| `list_jobs(session, page, per_page, filters)` | List jobs paginated |
| `update_job(session, job_id, data, updated_by_id)` | Update job |
| `delete_job(session, job_id)` | Soft delete job |
| `enable_job(session, job_id)` | Enable and schedule job |
| `disable_job(session, job_id)` | Disable and unschedule job |
| `trigger_job_now(session, job_id, triggered_by_user_id)` | Manual trigger |
| `pause_job(session, job_id)` | Pause job execution |
| `resume_job(session, job_id)` | Resume paused job |
| `get_job_history(session, job_id, filters, page, per_page)` | Job history |
| `get_all_history(session, filters, page, per_page)` | All history |
| `get_status(session)` | Scheduler status |
| `cleanup_history(session, retention_days)` | Clean old executions |

**Internal Methods**:
| Method | Description |
|--------|-------------|
| `_schedule_job(job)` | Add job to APScheduler |
| `_unschedule_job(job_id)` | Remove from APScheduler |
| `_create_execution_wrapper(job_id, job_key, func)` | Wrap job with tracking |
| `_execute_in_background(job_id, execution_id, user_id)` | Background execution |
| `_dispatch_to_celery(job_key, execution_id, user_id)` | Celery offload |
| `_update_heartbeat()` | Instance heartbeat |

**Dependencies**:
- `apscheduler.schedulers.asyncio.AsyncIOScheduler`
- `api.repositories.scheduler_repository`
- `db.models`

---

### Repository Layer

#### `src/backend/api/repositories/scheduler_repository.py`

**Purpose**: Database access layer for all scheduler entities.

**Key Exports**:
- `scheduler_repository` - Singleton instance

**Class: SchedulerRepository**

**Job Operations**:
| Method | Description |
|--------|-------------|
| `create_job(session, job_data)` | Insert new job |
| `get_job_by_id(session, job_id)` | Get job by ID |
| `get_jobs(session, filters, page, per_page)` | List jobs |
| `update_job(session, job_id, update_data)` | Update job fields |
| `soft_delete_job(session, job_id)` | Set is_active=False |

**Execution Operations**:
| Method | Description |
|--------|-------------|
| `create_execution(session, exec_data)` | Create execution record |
| `update_execution(session, execution_id, update_data)` | Update execution |
| `get_execution_by_id(session, execution_id)` | Get execution by UUID |
| `get_executions(session, job_id, filters, page, per_page)` | List executions |
| `get_running_execution(session, job_id)` | Check for running |
| `delete_old_executions(session, before_date)` | Cleanup old records |

**Lock Operations**:
| Method | Description |
|--------|-------------|
| `acquire_lock(session, job_id, execution_id, instance_id)` | Get lock |
| `release_lock(session, job_id, execution_id)` | Release lock |
| `check_lock(session, job_id)` | Check lock exists |
| `cleanup_expired_locks(session)` | Remove expired locks |

**Instance Operations**:
| Method | Description |
|--------|-------------|
| `register_instance(session, instance_data)` | Register scheduler |
| `update_heartbeat(session, instance_id)` | Update heartbeat |
| `get_active_instances(session)` | List active instances |
| `mark_instance_stopped(session, instance_id)` | Mark stopped |

**Lookup Operations**:
| Method | Description |
|--------|-------------|
| `get_task_functions(session)` | List task functions |
| `get_task_function_by_key(session, key)` | Get by key |
| `get_job_types(session)` | List job types |
| `get_execution_statuses(session)` | List statuses |
| `get_status_by_name(session, name)` | Get status by name |

---

### Schemas

#### `src/backend/api/schemas/scheduler_schemas.py`

**Purpose**: Pydantic request/response models.

**Request Schemas**:
| Schema | Purpose |
|--------|---------|
| `ScheduledJobCreate` | Create job request |
| `ScheduledJobUpdate` | Update job request |
| `JobActionRequest` | Action request (trigger/pause/etc) |
| `CleanupHistoryRequest` | Cleanup request |

**Response Schemas**:
| Schema | Purpose |
|--------|---------|
| `ScheduledJobResponse` | Full job response |
| `ScheduledJobListItem` | Job list item |
| `ScheduledJobExecutionResponse` | Execution details |
| `JobActionResponse` | Action result |
| `SchedulerStatusResponse` | Status info |
| `TaskFunctionResponse` | Task function info |
| `JobTypeResponse` | Job type info |
| `ExecutionStatusResponse` | Execution status |
| `PaginatedJobsResponse` | Paginated jobs |
| `PaginatedExecutionsResponse` | Paginated executions |

---

### Database Models

#### `src/backend/db/models.py`

**Scheduler Models**:

| Model | Table | Purpose |
|-------|-------|---------|
| `ScheduledJob` | `scheduled_job` | Job definitions |
| `ScheduledJobExecution` | `scheduled_job_execution` | Execution history |
| `ScheduledJobLock` | `scheduled_job_lock` | Distributed locks |
| `SchedulerInstance` | `scheduler_instance` | Instance registry |
| `TaskFunction` | `task_function` | Available tasks |
| `SchedulerJobType` | `scheduler_job_type` | Job types |
| `SchedulerExecutionStatus` | `scheduler_execution_status` | Statuses |

**Relationships**:
```
ScheduledJob ──┬── TaskFunction (M:1)
               ├── SchedulerJobType (M:1)
               ├── ScheduledJobExecution (1:M)
               └── ScheduledJobLock (1:M)

ScheduledJobExecution ── SchedulerExecutionStatus (M:1)
```

---

### Celery Tasks

#### `src/backend/tasks/scheduler.py`

**Purpose**: Celery tasks for scheduler operations.

**Tasks**:
| Task | Purpose |
|------|---------|
| `cleanup_history_task` | Clean old execution records |

**Utilities**:
| Function | Purpose |
|----------|---------|
| `_run_async(coro)` | Run async in Celery/gevent |

---

## Frontend Modules

### Pages

#### `src/my-app/app/(pages)/scheduler/page.tsx`

**Purpose**: Main scheduler dashboard page.

**Features**:
- Job list with pagination
- Create/edit job sheets
- Job action buttons
- Status panel

---

### Components

#### `src/my-app/app/(pages)/scheduler/_components/`

| File | Purpose |
|------|---------|
| `scheduler-body.tsx` | Main container |
| `table/scheduler-table.tsx` | Job listing table |
| `table/scheduler-table-columns.tsx` | Table column definitions |
| `table/scheduler-table-actions.tsx` | Row action buttons |
| `modal/create-job-sheet.tsx` | Create job dialog |
| `modal/edit-job-sheet.tsx` | Edit job dialog |
| `modal/view-job-sheet.tsx` | View job details |
| `sidebar/status-panel.tsx` | Scheduler status panel |

---

### Types

#### `src/my-app/types/scheduler.ts`

**Purpose**: TypeScript type definitions.

**Interfaces**:
| Interface | Purpose |
|-----------|---------|
| `ScheduledJob` | Job data structure |
| `ScheduledJobExecution` | Execution record |
| `SchedulerStatus` | Status info |
| `TaskFunction` | Task function |
| `JobType` | Job type |
| `ExecutionStatus` | Execution status |

**Types**:
| Type | Purpose |
|------|---------|
| `JobAction` | Action union type |
| `CreateJobRequest` | Create request |
| `UpdateJobRequest` | Update request |
| `JobActionRequest` | Action request |

---

### Actions

#### `src/my-app/lib/actions/scheduler.actions.ts`

**Purpose**: Server actions for API calls.

**Functions**:
| Function | Purpose |
|----------|---------|
| `createJob(data)` | Create new job |
| `updateJob(id, data)` | Update job |
| `deleteJob(id)` | Delete job |
| `performJobAction(id, action)` | Execute action |
| `getJobs(page, perPage)` | List jobs |
| `getJob(id)` | Get single job |
| `getJobHistory(id, page, perPage)` | Get history |
| `getSchedulerStatus()` | Get status |

---

### Hooks

#### `src/my-app/hooks/use-scheduler-jobs.ts`

**Purpose**: Custom hook for job list management.

**Exports**:
| Hook | Purpose |
|------|---------|
| `useSchedulerJobs(options)` | Fetch and manage job list |

**Options**:
- `page: number`
- `perPage: number`
- `autoRefresh: boolean`
- `refreshInterval: number`

**Returns**:
- `jobs: ScheduledJob[]`
- `total: number`
- `isLoading: boolean`
- `error: string | null`
- `refresh: () => void`

---

### API Routes (Next.js)

#### `src/my-app/app/api/scheduler/`

| Route | Methods | Purpose |
|-------|---------|---------|
| `jobs/route.ts` | GET, POST | List/create jobs |
| `jobs/[id]/route.ts` | GET, PUT, DELETE | Job CRUD |
| `jobs/[id]/action/route.ts` | POST | Job actions |
| `jobs/[id]/history/route.ts` | GET | Job history |
| `status/route.ts` | GET | Scheduler status |

---

### Internationalization

#### `src/my-app/locales/en/scheduler.json`

English translations for scheduler UI.

**Keys**:
- `title`, `description`
- `table.*` (column headers)
- `actions.*` (button labels)
- `status.*` (status messages)
- `form.*` (form labels)
- `toast.*` (notification messages)

#### `src/my-app/locales/ar/scheduler.json`

Arabic translations (RTL support).

---

## Context Providers

#### `src/my-app/app/(pages)/scheduler/context/scheduler-actions-context.tsx`

**Purpose**: State management for scheduler page actions.

**Exports**:
| Export | Purpose |
|--------|---------|
| `SchedulerActionsProvider` | Context provider |
| `useSchedulerActions()` | Context hook |

**State**:
- `selectedJob: ScheduledJob | null`
- `isCreateOpen: boolean`
- `isEditOpen: boolean`
- `isViewOpen: boolean`

---

## Database Migrations

#### `src/backend/alembic/versions/`

Scheduler-related migrations:

| File | Description |
|------|-------------|
| `*_create_scheduler_tables.py` | Initial scheduler tables |
| `*_add_task_function.py` | Add task function table |
| `*_add_execution_tracking.py` | Add execution fields |
| `*_add_distributed_locking.py` | Add lock table |

---

## Configuration

### Backend Settings

In `src/backend/settings.py`:

```python
# Scheduler settings (if applicable)
SCHEDULER_MODE: str = "embedded"  # or "standalone"
SCHEDULER_TIMEZONE: str = "UTC"
SCHEDULER_MISFIRE_GRACE_TIME: int = 60
SCHEDULER_MAX_INSTANCES: int = 1
```

### Environment Variables

```env
# Scheduler (optional overrides)
SCHEDULER_MODE=embedded
SCHEDULER_TIMEZONE=UTC
```

---

## File Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                     API Routes                              │
│  src/backend/api/v1/scheduler.py                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  src/backend/api/services/scheduler_service.py              │
│  ├── APScheduler (AsyncIOScheduler)                         │
│  └── Celery dispatch                                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repository Layer                           │
│  src/backend/api/repositories/scheduler_repository.py       │
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database Models                           │
│  src/backend/db/models.py                                   │
│  ├── ScheduledJob                                           │
│  ├── ScheduledJobExecution                                  │
│  ├── ScheduledJobLock                                       │
│  └── SchedulerInstance                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Celery Tasks                             │
│  src/backend/tasks/scheduler.py                             │
│  └── Uses scheduler_service for async operations            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      Schemas                                │
│  src/backend/api/schemas/scheduler_schemas.py               │
│  └── Inherits from CamelModel                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Where to Add New Code

| What | Where |
|------|-------|
| New API endpoint | `src/backend/api/v1/scheduler.py` |
| New business logic | `src/backend/api/services/scheduler_service.py` |
| New DB operation | `src/backend/api/repositories/scheduler_repository.py` |
| New schema | `src/backend/api/schemas/scheduler_schemas.py` |
| New Celery task | `src/backend/tasks/scheduler.py` |
| New frontend component | `src/my-app/app/(pages)/scheduler/_components/` |
| New TypeScript type | `src/my-app/types/scheduler.ts` |
| New server action | `src/my-app/lib/actions/scheduler.actions.ts` |
| New hook | `src/my-app/hooks/use-scheduler-*.ts` |
| New translation | `src/my-app/locales/{lang}/scheduler.json` |
