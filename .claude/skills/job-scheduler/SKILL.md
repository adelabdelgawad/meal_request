---
name: job-scheduler
description: |
  Manages APScheduler-based background job scheduling and execution. Use when working with
  scheduled jobs, cron jobs, interval jobs, job triggers, execution history, or Celery tasks.
  Covers CRUD operations, manual triggers, distributed locking, and scheduler status monitoring.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Job Scheduler Management

## Overview

The Job Scheduler system manages background task execution using:

- **APScheduler** - Core scheduling engine (AsyncIOScheduler)
- **FastAPI** - REST API layer
- **SQLAlchemy** - Async database operations
- **Celery** - Long-running task offloading

**Capabilities**: Interval jobs, cron jobs, manual triggers, execution history, distributed locking, multi-instance coordination.

> **CRITICAL**: Reuse existing patterns. Do not introduce new scheduling frameworks.

## When to Use This Skill

Activate when request involves:

- Creating/modifying scheduled jobs
- Cron or interval scheduling
- Job triggers, pause, resume, enable, disable
- Execution history or cleanup
- Scheduler status monitoring
- Background job processing
- Celery scheduler tasks

## Quick Reference

### Backend Locations

| Component | Path |
|-----------|------|
| API Router | `src/backend/api/v1/scheduler.py` |
| Service | `src/backend/api/services/scheduler_service.py` |
| Repository | `src/backend/api/repositories/scheduler_repository.py` |
| Schemas | `src/backend/api/schemas/scheduler_schemas.py` |
| Models | `src/backend/db/models.py` |
| Celery Tasks | `src/backend/tasks/scheduler.py` |

### Frontend Locations

| Component | Path |
|-----------|------|
| Dashboard | `src/my-app/app/(pages)/scheduler/page.tsx` |
| Components | `src/my-app/app/(pages)/scheduler/_components/` |
| Types | `src/my-app/types/scheduler.ts` |
| Actions | `src/my-app/lib/actions/scheduler.actions.ts` |
| Hooks | `src/my-app/hooks/use-scheduler-jobs.ts` |

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/scheduler/jobs` | Create job |
| GET | `/scheduler/jobs` | List jobs |
| GET | `/scheduler/jobs/{id}` | Get job |
| PUT | `/scheduler/jobs/{id}` | Update job |
| DELETE | `/scheduler/jobs/{id}` | Delete job |
| POST | `/scheduler/jobs/{id}/action` | Trigger/pause/resume/enable/disable |
| GET | `/scheduler/jobs/{id}/history` | Execution history |
| GET | `/scheduler/status` | Scheduler status |

For complete API documentation, see [REFERENCE.md](REFERENCE.md).

## Core Concepts

### ScheduledJob Model

```python
# Key fields
task_function_id: int       # What to execute
job_type_id: int            # 1=interval, 2=cron

# Interval (mutually exclusive with cron)
interval_seconds/minutes/hours/days: Optional[int]

# Cron
cron_expression: Optional[str]  # e.g., "0 2 * * *"

# Execution settings
priority: int = 0           # Higher runs first
max_instances: int = 1      # Parallel limit (1-10)
misfire_grace_time: int = 60  # Seconds for missed jobs
coalesce: bool = True       # Combine missed runs

# Status
is_enabled: bool = True     # Can be scheduled
is_active: bool = True      # Soft delete flag
```

### Execution Lifecycle

```
pending → running → success
                 ↘ failed
```

### Distributed Locking

Prevents duplicate execution across instances via `ScheduledJobLock` table. Locks expire after 1 hour.

For detailed model documentation, see [REFERENCE.md](REFERENCE.md).

## Allowed Operations

**DO:**
- Add API endpoints following existing patterns
- Extend `SchedulerService` methods
- Add job actions (following action pattern)
- Update frontend scheduler components
- Add/update tests

**DON'T:**
- Bypass service layer
- Call APScheduler directly from routes
- Add new background systems (RQ, threads)
- Modify HRIS/attendance logic

## Implementation Patterns

For Celery task patterns, async patterns, and code examples, see:
- [PATTERNS.md](PATTERNS.md) - Implementation patterns
- [EXAMPLES.md](EXAMPLES.md) - Usage examples

## Validation Checklist

Before completing scheduler work:

- [ ] Existing patterns reused
- [ ] Service layer contains logic
- [ ] Repository layer for DB operations
- [ ] Schemas inherit from `CamelModel`
- [ ] Async/await used correctly
- [ ] Tests updated

## Utility Scripts

Validate cron expressions:
```bash
python .claude/skills/job-scheduler/scripts/validate_cron.py "0 2 * * *"
```

Check job status (requires running backend):
```bash
python .claude/skills/job-scheduler/scripts/check_job.py --job-id 1
```

## Additional Resources

- [REFERENCE.md](REFERENCE.md) - Complete API and model documentation
- [EXAMPLES.md](EXAMPLES.md) - Code examples for common operations
- [PATTERNS.md](PATTERNS.md) - Implementation patterns (Celery, async)
- [MODULES.md](MODULES.md) - Complete module inventory

## Scope Boundaries

This skill applies **ONLY** to the job scheduler system.

**NOT covered:**
- Employee shifts (read-only from TMS)
- Attendance records (read-only)
- HRIS synchronization logic

If request involves both scheduler and HRIS, apply this skill only to scheduler portion.
