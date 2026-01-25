# Celery Task Reference

Quick reference for Celery task development in this project.

## File Locations

| Component | Path |
|-----------|------|
| Celery App | `src/backend/celery_app.py` |
| Celery Bridge | `src/backend/celery_bridge.py` |
| HRIS Tasks | `src/backend/tasks/hris.py` |
| Email Tasks | `src/backend/tasks/email.py` |
| Attendance Tasks | `src/backend/tasks/attendance.py` |
| Scheduler Tasks | `src/backend/tasks/scheduler.py` |

## Database Connections

### Primary Database (MariaDB)

```python
from db.maria_database import DatabaseSessionLocal, database_engine

async with DatabaseSessionLocal() as session:
    # Use session for queries
    ...

# Always dispose in finally
await database_engine.dispose()
```

### HRIS Database (SQL Server)

```python
from db.hris_database import _get_hris_session_maker, dispose_hris_engine

HrisSession = _get_hris_session_maker()
async with HrisSession() as session:
    # Use session for queries
    ...

# Always dispose in finally
await dispose_hris_engine()
```

### BioStar Database (MSSQL)

```python
from db.biostar_database import _get_biostar_session_maker, dispose_biostar_engine

BiostarSession = _get_biostar_session_maker()
async with BiostarSession() as session:
    # Use session for queries
    ...

# Always dispose in finally
await dispose_biostar_engine()
```

## Task Decorator Options

| Option | Type | Description |
|--------|------|-------------|
| `bind` | bool | Access `self` for task metadata and retry methods |
| `max_retries` | int | Maximum number of retry attempts |
| `default_retry_delay` | int | Seconds between retries |
| `autoretry_for` | tuple | Exception types to auto-retry |
| `retry_backoff` | bool | Use exponential backoff |
| `retry_backoff_max` | int | Maximum backoff delay in seconds |
| `retry_jitter` | bool | Add random jitter to prevent thundering herd |
| `soft_time_limit` | int | Seconds before SoftTimeLimitExceeded raised |
| `time_limit` | int | Seconds before task is killed |
| `rate_limit` | str | Rate limit (e.g., "10/m" for 10 per minute) |
| `ignore_result` | bool | Don't store task result |

## Task Request Properties

When using `bind=True`:

```python
@shared_task(bind=True)
def my_task(self, ...):
    self.request.id           # Unique task ID
    self.request.retries      # Current retry count
    self.request.args         # Positional arguments
    self.request.kwargs       # Keyword arguments
    self.request.hostname     # Worker hostname
    self.request.delivery_info  # Routing info
    self.max_retries          # Max retry setting
```

## Manual Retry

```python
@shared_task(bind=True, max_retries=3)
def my_task(self, ...):
    try:
        ...
    except SomeError as e:
        # Retry with countdown
        raise self.retry(exc=e, countdown=60)
```

## Execution Status Codes

| Code | Description |
|------|-------------|
| `pending` | Task created, not started |
| `running` | Task currently executing |
| `success` | Task completed successfully |
| `failed` | Task failed (may have retried) |
| `cancelled` | Task was cancelled |

## Scheduler Repository Methods

```python
from api.repositories.scheduler_repository import SchedulerRepository

scheduler_repo = SchedulerRepository()

# Get execution status by code
status = await scheduler_repo.get_execution_status_by_code(session, "success")

# Update execution
await scheduler_repo.update_execution(
    session,
    execution_id,
    {
        "completed_at": datetime.now(timezone.utc),
        "duration_ms": 1234,
        "status_id": status.id,
        "result_summary": "Completed successfully",
        "error_message": None,  # Or error message on failure
    },
)
```

## Structured Logging

```python
from utils.structured_logger import get_structured_logger
import socket

structured_logger = get_structured_logger(__name__)

# Log task start
structured_logger.log_celery_task_start(
    task_name="my_task",
    execution_id="uuid-string",
    celery_task_id=self.request.id,
    worker_host=socket.gethostname(),
    triggered_by="user-id-or-none",
    task_metadata={"retries": 0, "max_retries": 3},
)

# Log task completion
structured_logger.log_celery_task_complete(
    task_name="my_task",
    execution_id="uuid-string",
    final_status="SUCCESS",  # or "FAILED"
    duration_ms=1234,
    error_message=None,  # Or error message on failure
)
```

## Common Commands

```bash
# Start worker
celery -A celery_app worker -P gevent --loglevel=info

# Start worker with beat scheduler
celery -A celery_app worker -P gevent --loglevel=info -B

# Run specific task manually
celery -A celery_app call tasks.hris.hris_replication_task

# Monitor tasks
celery -A celery_app events

# Check worker status
celery -A celery_app inspect active

# Purge all tasks
celery -A celery_app purge
```

## Error Types

| Error | Cause | Solution |
|-------|-------|----------|
| `Task got Future attached to a different loop` | Using `asyncio.run()` directly | Use `_run_async()` helper |
| `Event loop is closed` | Disposing engine outside `_execute()` | Move dispose to finally inside `_execute()` |
| `Connection pool exhausted` | Not disposing engines | Add `await engine.dispose()` in finally |
| `SoftTimeLimitExceeded` | Task exceeded soft time limit | Optimize or increase limit |

## Task Registration

Tasks triggered by APScheduler must be registered in the bridge:

```python
# src/backend/celery_bridge.py

from tasks.my_module import my_task

TASK_REGISTRY = {
    "my_task_code": my_task,
    # ... other tasks
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CELERY_BROKER_URL` | Redis URL for task queue |
| `CELERY_RESULT_BACKEND` | Redis URL for results |
| `CELERY_TASK_ALWAYS_EAGER` | Run tasks synchronously (testing) |

## Testing Tasks

```python
# Direct execution (no Celery)
from tasks.my_task import my_task

result = my_task.apply(args=["arg1"]).get()

# Async execution
result = my_task.delay("arg1")
result.get(timeout=30)  # Wait for result
```
