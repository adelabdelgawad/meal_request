# Job Scheduler Examples

Concrete code examples for common scheduler operations.

## Backend Examples

### Adding a New API Endpoint

Add endpoint to `src/backend/api/v1/scheduler.py`:

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.scheduler_schemas import (
    ScheduledJobResponse,
    PaginatedJobsResponse,
)
from api.services.scheduler_service import scheduler_service
from db.maria_database import get_session
from utils.auth import get_current_super_admin
from db.models import Account

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get("/jobs/primary", response_model=list[ScheduledJobResponse])
async def get_primary_jobs(
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
) -> list[ScheduledJobResponse]:
    """Get all primary (critical) jobs."""
    jobs, _ = await scheduler_service.list_jobs(
        session,
        page=1,
        per_page=100,
        filters={"is_primary": True},
    )
    return jobs
```

### Adding a Service Method

Add method to `src/backend/api/services/scheduler_service.py`:

```python
async def get_jobs_by_task_function(
    self,
    session: AsyncSession,
    task_function_key: str,
) -> list[ScheduledJob]:
    """Get all jobs for a specific task function."""
    from api.repositories.scheduler_repository import scheduler_repository

    # Get task function by key
    task_functions = await scheduler_repository.get_task_functions(session)
    task_func = next(
        (tf for tf in task_functions if tf.key == task_function_key),
        None
    )
    if not task_func:
        raise ValueError(f"Task function not found: {task_function_key}")

    jobs, _ = await scheduler_repository.get_jobs(
        session,
        filters={"task_function_id": task_func.id, "is_active": True},
        page=1,
        per_page=1000,
    )
    return jobs
```

### Adding a Repository Method

Add method to `src/backend/api/repositories/scheduler_repository.py`:

```python
async def get_failed_executions_since(
    self,
    session: AsyncSession,
    since: datetime,
    job_id: Optional[int] = None,
) -> list[ScheduledJobExecution]:
    """Get all failed executions since a given datetime."""
    from sqlalchemy import select
    from db.models import ScheduledJobExecution, SchedulerExecutionStatus

    # Get failed status ID
    failed_status = await session.scalar(
        select(SchedulerExecutionStatus).where(
            SchedulerExecutionStatus.name == "failed"
        )
    )

    query = (
        select(ScheduledJobExecution)
        .where(ScheduledJobExecution.status_id == failed_status.id)
        .where(ScheduledJobExecution.created_at >= since)
    )

    if job_id:
        query = query.where(ScheduledJobExecution.job_id == job_id)

    query = query.order_by(ScheduledJobExecution.created_at.desc())

    result = await session.execute(query)
    return list(result.scalars().all())
```

### Creating a New Schema

Add schema to `src/backend/api/schemas/scheduler_schemas.py`:

```python
from api.schemas._base import CamelModel
from typing import Optional
from datetime import datetime


class JobStatisticsResponse(CamelModel):
    """Statistics for a scheduled job."""
    job_id: int
    job_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_ms: Optional[float]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    success_rate: float  # 0.0 to 1.0


class SchedulerHealthResponse(CamelModel):
    """Health check response for scheduler."""
    healthy: bool
    scheduler_running: bool
    database_connected: bool
    active_instances: int
    pending_jobs: int
    issues: list[str]
```

### Adding a Celery Task

Add task to `src/backend/tasks/scheduler.py`:

```python
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine handling Celery/gevent event loops."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        logger.debug("Detected running event loop - running in new thread")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        logger.debug("No running event loop - using run_until_complete")
        return loop.run_until_complete(coro)


@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def notify_failed_jobs_task(
    self,
    execution_id: str,
    hours_back: int = 24,
    triggered_by_user_id: str = None,
) -> dict:
    """Send notifications for failed jobs in the last N hours."""

    async def _execute():
        from db.maria_database import DatabaseSessionLocal, database_engine
        from datetime import datetime, timedelta, timezone

        result = None
        try:
            async with DatabaseSessionLocal() as session:
                from api.repositories.scheduler_repository import scheduler_repository

                since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                failed = await scheduler_repository.get_failed_executions_since(
                    session, since
                )

                # Send notifications (implement your notification logic)
                notification_count = len(failed)

                result = {
                    "status": "success",
                    "failed_jobs_found": notification_count,
                    "notifications_sent": notification_count,
                }

        except Exception as e:
            logger.error(f"Failed to notify: {e}")
            raise
        finally:
            logger.debug("Disposing database engine...")
            try:
                await database_engine.dispose()
            except Exception as e:
                logger.warning(f"Failed to dispose engine: {e}")

        return result

    try:
        logger.info(f"Starting notify_failed_jobs_task for last {hours_back} hours")
        result = _run_async(_execute())
        logger.info(f"Task completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

---

## Frontend Examples

### Adding a New Component

Create `src/my-app/app/(pages)/scheduler/_components/job-stats-card.tsx`:

```tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useTranslations } from "next-intl";

interface JobStatsCardProps {
  totalJobs: number;
  enabledJobs: number;
  runningExecutions: number;
}

export function JobStatsCard({
  totalJobs,
  enabledJobs,
  runningExecutions,
}: JobStatsCardProps) {
  const t = useTranslations("scheduler");

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold">{totalJobs}</div>
            <div className="text-sm text-muted-foreground">
              {t("stats.totalJobs")}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {enabledJobs}
            </div>
            <div className="text-sm text-muted-foreground">
              {t("stats.enabledJobs")}
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {runningExecutions}
            </div>
            <div className="text-sm text-muted-foreground">
              {t("stats.running")}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Adding a Server Action

Add action to `src/my-app/lib/actions/scheduler.actions.ts`:

```typescript
"use server";

import { getAuthHeaders } from "@/lib/auth";
import { revalidatePath } from "next/cache";

const API_URL = process.env.BACKEND_URL;

export async function triggerJobAction(jobId: number): Promise<{
  success: boolean;
  executionId?: string;
  error?: string;
}> {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(
      `${API_URL}/api/v1/scheduler/jobs/${jobId}/action`,
      {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ action: "trigger" }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { success: false, error: error.detail || "Failed to trigger job" };
    }

    const data = await response.json();
    revalidatePath("/scheduler");

    return {
      success: true,
      executionId: data.executionId,
    };
  } catch (error) {
    console.error("Error triggering job:", error);
    return { success: false, error: "Network error" };
  }
}

export async function getJobHistory(
  jobId: number,
  page: number = 1,
  perPage: number = 10
) {
  try {
    const headers = await getAuthHeaders();

    const response = await fetch(
      `${API_URL}/api/v1/scheduler/jobs/${jobId}/history?page=${page}&per_page=${perPage}`,
      {
        headers,
        next: { revalidate: 30 }, // Cache for 30 seconds
      }
    );

    if (!response.ok) {
      throw new Error("Failed to fetch job history");
    }

    return await response.json();
  } catch (error) {
    console.error("Error fetching job history:", error);
    return { items: [], total: 0 };
  }
}
```

### Adding a Custom Hook

Create `src/my-app/hooks/use-job-history.ts`:

```typescript
"use client";

import { useState, useEffect, useCallback } from "react";
import { ScheduledJobExecution } from "@/types/scheduler";

interface UseJobHistoryOptions {
  jobId: number;
  page?: number;
  perPage?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface UseJobHistoryReturn {
  executions: ScheduledJobExecution[];
  total: number;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useJobHistory({
  jobId,
  page = 1,
  perPage = 10,
  autoRefresh = false,
  refreshInterval = 5000,
}: UseJobHistoryOptions): UseJobHistoryReturn {
  const [executions, setExecutions] = useState<ScheduledJobExecution[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(
        `/api/scheduler/jobs/${jobId}/history?page=${page}&per_page=${perPage}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch history");
      }

      const data = await response.json();
      setExecutions(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  }, [jobId, page, perPage]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchHistory, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchHistory]);

  return {
    executions,
    total,
    isLoading,
    error,
    refresh: fetchHistory,
  };
}
```

### Adding i18n Translations

Add to `src/my-app/locales/en/scheduler.json`:

```json
{
  "stats": {
    "title": "Job Statistics",
    "totalJobs": "Total Jobs",
    "enabledJobs": "Enabled",
    "running": "Running"
  },
  "history": {
    "title": "Execution History",
    "noHistory": "No execution history found",
    "columns": {
      "executionId": "Execution ID",
      "scheduledAt": "Scheduled At",
      "startedAt": "Started At",
      "completedAt": "Completed At",
      "duration": "Duration",
      "status": "Status"
    }
  },
  "actions": {
    "trigger": "Trigger Now",
    "triggerSuccess": "Job triggered successfully",
    "triggerError": "Failed to trigger job"
  }
}
```

Add to `src/my-app/locales/ar/scheduler.json`:

```json
{
  "stats": {
    "title": "إحصائيات المهام",
    "totalJobs": "إجمالي المهام",
    "enabledJobs": "مفعلة",
    "running": "قيد التشغيل"
  },
  "history": {
    "title": "سجل التنفيذ",
    "noHistory": "لا يوجد سجل تنفيذ",
    "columns": {
      "executionId": "معرف التنفيذ",
      "scheduledAt": "المجدول في",
      "startedAt": "بدأ في",
      "completedAt": "اكتمل في",
      "duration": "المدة",
      "status": "الحالة"
    }
  },
  "actions": {
    "trigger": "تشغيل الآن",
    "triggerSuccess": "تم تشغيل المهمة بنجاح",
    "triggerError": "فشل تشغيل المهمة"
  }
}
```

---

## Testing Examples

### Backend Unit Test

Create `src/backend/tests/test_scheduler_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from api.services.scheduler_service import SchedulerService
from api.schemas.scheduler_schemas import ScheduledJobCreate
from db.models import ScheduledJob, TaskFunction, SchedulerJobType


@pytest.fixture
def scheduler_service():
    return SchedulerService()


@pytest.fixture
def mock_session():
    session = AsyncMock()
    return session


@pytest.fixture
def sample_job_create():
    return ScheduledJobCreate(
        task_function_id=1,
        name_en="Test Job",
        interval_minutes=30,
        priority=5,
        is_enabled=True,
    )


@pytest.mark.asyncio
async def test_create_interval_job(scheduler_service, mock_session, sample_job_create):
    """Test creating an interval job."""
    # Arrange
    mock_task_func = TaskFunction(id=1, key="test_task", name_en="Test Task")
    mock_job_type = SchedulerJobType(id=1, name="interval")

    mock_session.scalar = AsyncMock(side_effect=[mock_task_func, mock_job_type])
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Act
    result = await scheduler_service.create_job(
        mock_session,
        sample_job_create,
        created_by_id="user-123",
    )

    # Assert
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_job_creates_execution(scheduler_service, mock_session):
    """Test that triggering a job creates an execution record."""
    # Arrange
    mock_job = ScheduledJob(
        id=1,
        task_function_id=1,
        job_type_id=1,
        is_enabled=True,
        is_active=True,
    )

    # Act & Assert
    # ... implementation
    pass
```

### Frontend Component Test

Create `src/my-app/app/(pages)/scheduler/_components/__tests__/job-stats-card.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { JobStatsCard } from "../job-stats-card";
import { NextIntlClientProvider } from "next-intl";

const messages = {
  scheduler: {
    stats: {
      title: "Job Statistics",
      totalJobs: "Total Jobs",
      enabledJobs: "Enabled",
      running: "Running",
    },
  },
};

describe("JobStatsCard", () => {
  it("renders job statistics correctly", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <JobStatsCard
          totalJobs={15}
          enabledJobs={12}
          runningExecutions={2}
        />
      </NextIntlClientProvider>
    );

    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Job Statistics")).toBeInTheDocument();
  });
});
```
