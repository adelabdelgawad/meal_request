"""
Scheduler Endpoints - APScheduler task management.

Provides full management of scheduled jobs:
- Create, update, delete jobs
- Enable, disable, trigger, pause, resume jobs
- View execution history
- Monitor scheduler status
"""

import math
from datetime import datetime
from typing import Optional

import icecream
from fastapi import APIRouter, Depends, Query, status

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from api.schemas.scheduler_schemas import (
    CleanupRequest,
    CleanupResponse,
    JobAction,
    JobActionRequest,
    JobActionResponse,
    JobExecutionListResponse,
    ScheduledJobCreate,
    ScheduledJobCronCreate,
    ScheduledJobIntervalCreate,
    ScheduledJobListResponse,
    ScheduledJobResponse,
    ScheduledJobUpdate,
    SchedulerExecutionStatusListResponse,
    SchedulerJobTypeListResponse,
    SchedulerStatusResponse,
    TaskFunctionListResponse,
)
from api.services.scheduler_service import get_scheduler_service
from utils.security import require_super_admin
from utils.structured_logger import (
    get_structured_logger,
    set_execution_context,
)

router = APIRouter(prefix="/setting/scheduler", tags=["setting-scheduler"])
structured_logger = get_structured_logger(__name__)


# -------------------
# Job Creation
# -------------------


@router.post(
    "/jobs/interval",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_interval_job(
    data: ScheduledJobIntervalCreate,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Create a new interval-based scheduled job. Requires Super Admin role."""
    service = get_scheduler_service()
    job = await service.create_interval_job(
        session,
        data,
        created_by_id=payload.get("user_id") or payload.get("sub"),
    )
    await session.commit()
    return await service._to_job_response(session, job)


@router.post(
    "/jobs/cron",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cron_job(
    data: ScheduledJobCronCreate,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Create a new cron-based scheduled job. Requires Super Admin role."""
    service = get_scheduler_service()
    job = await service.create_cron_job(
        session,
        data,
        created_by_id=payload.get("user_id") or payload.get("sub"),
    )
    await session.commit()
    return await service._to_job_response(session, job)


# -------------------
# Job CRUD
# -------------------


@router.get("/jobs", response_model=ScheduledJobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    is_enabled: Optional[bool] = None,
    job_type_id: Optional[int] = None,
    task_function_id: Optional[int] = None,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """List all scheduled jobs with pagination. Requires Super Admin role."""
    service = get_scheduler_service()
    jobs, total = await service.list_jobs(
        session, page, per_page, is_enabled, job_type_id, task_function_id
    )

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    icecream.ic(jobs)
    return ScheduledJobListResponse(
        items=jobs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/jobs/{job_id}", response_model=ScheduledJobResponse)
async def get_job(
    job_id: str,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Get a scheduled job by ID. Requires Super Admin role."""
    service = get_scheduler_service()
    return await service.get_job(session, job_id)


@router.put("/jobs/{job_id}", response_model=ScheduledJobResponse)
async def update_job(
    job_id: str,
    data: ScheduledJobUpdate,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Update a scheduled job. Requires Super Admin role."""
    service = get_scheduler_service()
    job = await service.update_job(
        session,
        job_id,
        data,
        updated_by_id=payload.get("user_id") or payload.get("sub"),
    )
    await session.commit()
    return await service._to_job_response(session, job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Delete (soft) a scheduled job. Requires Super Admin role."""
    service = get_scheduler_service()
    await service.delete_job(session, job_id)
    await session.commit()
    return None


# -------------------
# Job Actions
# -------------------


@router.post("/jobs/{job_id}/action", response_model=JobActionResponse)
async def perform_job_action(
    job_id: str,
    action_request: JobActionRequest,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Perform an action on a job (enable, disable, trigger, pause, resume). Requires Super Admin role."""
    service = get_scheduler_service()
    action = action_request.action
    execution_id = None
    job_response = None
    message = ""

    if action == JobAction.ENABLE:
        await service.enable_job(session, job_id)
        message = "Job enabled successfully"
    elif action == JobAction.DISABLE:
        await service.disable_job(session, job_id)
        message = "Job disabled successfully"
    elif action == JobAction.TRIGGER:
        # INSTRUMENTATION POINT 1: API entry point for manual trigger
        # Extract user ID from JWT payload for audit logging
        user_id = payload.get("user_id") or payload.get("sub")

        structured_logger.log_api_entry(
            job_id=job_id,
            action="trigger",
            user_id=user_id,
            endpoint="/scheduler/jobs/{job_id}/action",
            method="POST",
        )

        # Set execution context for downstream logging
        set_execution_context(
            job_id=job_id,
            user_id=user_id,
            trigger_source="API",
            action="trigger",
        )

        execution_id, updated_job = await service.trigger_job_now(
            session, job_id, triggered_by_user_id=user_id
        )
        message = f"Job triggered, execution ID: {execution_id}"

        # Convert job to response model using service's _to_job_response for proper field mapping
        job_response = await service._to_job_response(session, updated_job)

        # Log successful trigger
        import logging

        logger = logging.getLogger(__name__)
        logger.info(
            f"[TRIGGER ENDPOINT] job_response.current_execution_status={job_response.current_execution_status}"
        )

        # Structured log for successful trigger
        structured_logger.info(
            event="API_TRIGGER_SUCCESS",
            message=f"Job {job_id} triggered successfully",
            job_id=job_id,
            execution_id=execution_id,
            user_id=user_id,
        )
    elif action == JobAction.PAUSE:
        await service.pause_job(session, job_id)
        message = "Job paused successfully"
    elif action == JobAction.RESUME:
        await service.resume_job(session, job_id)
        message = "Job resumed successfully"

    await session.commit()

    return JobActionResponse(
        success=True,
        message=message,
        job_id=job_id,
        action=action.value,
        execution_id=execution_id,
        job=job_response,
    )


# -------------------
# Execution History
# -------------------


@router.get("/jobs/{job_id}/history", response_model=JobExecutionListResponse)
async def get_job_history(
    job_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Get execution history for a specific job. Requires Super Admin role."""
    service = get_scheduler_service()
    executions, total = await service.get_job_history(
        session, job_id, status_id, from_date, to_date, page, per_page
    )

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return JobExecutionListResponse(
        items=executions,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get("/history", response_model=JobExecutionListResponse)
async def get_all_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status_id: Optional[int] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Get execution history across all jobs. Requires Super Admin role."""
    service = get_scheduler_service()
    executions, total = await service.get_all_history(
        session, status_id, from_date, to_date, page, per_page
    )

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return JobExecutionListResponse(
        items=executions,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


# -------------------
# Scheduler Status
# -------------------


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status(
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Get overall scheduler status and statistics. Requires Super Admin role."""
    service = get_scheduler_service()
    return await service.get_status(session)


# -------------------
# Cleanup
# -------------------


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_history(
    cleanup_request: CleanupRequest = CleanupRequest(),
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Clean up old execution history and stale data. Requires Super Admin role."""
    service = get_scheduler_service()
    result = await service.cleanup_history(session, cleanup_request.retention_days)

    return CleanupResponse(
        success=True,
        deleted_executions=result["deleted_executions"],
        deleted_locks=result["deleted_locks"],
        deleted_instances=result["deleted_instances"],
        message=f"Cleanup completed: {result['deleted_executions']} executions, "
        f"{result['deleted_locks']} locks, {result['deleted_instances']} instances deleted",
    )


# -------------------
# Lookup Tables
# -------------------


@router.get("/task-functions", response_model=TaskFunctionListResponse)
async def list_task_functions(
    is_active: Optional[bool] = True,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """List all available task functions. Requires Super Admin role."""
    service = get_scheduler_service()
    task_functions = await service.list_task_functions(session, is_active)

    return TaskFunctionListResponse(
        items=task_functions,
        total=len(task_functions),
    )


@router.get("/job-types", response_model=SchedulerJobTypeListResponse)
async def list_job_types(
    is_active: Optional[bool] = True,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """List all available job types. Requires Super Admin role."""
    service = get_scheduler_service()
    job_types = await service.list_job_types(session, is_active)

    return SchedulerJobTypeListResponse(
        items=job_types,
        total=len(job_types),
    )


@router.get("/execution-statuses", response_model=SchedulerExecutionStatusListResponse)
async def list_execution_statuses(
    is_active: Optional[bool] = True,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """List all execution statuses. Requires Super Admin role."""
    service = get_scheduler_service()
    statuses = await service.list_execution_statuses(session, is_active)

    return SchedulerExecutionStatusListResponse(
        items=statuses,
        total=len(statuses),
    )


# -------------------
# Unified Job Creation
# -------------------


@router.post(
    "/jobs",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    data: ScheduledJobCreate,
    session: SessionDep,
    payload: dict = Depends(require_super_admin),
):
    """Create a new scheduled job using task function and job type IDs. Requires Super Admin role."""
    service = get_scheduler_service()
    job = await service.create_job(
        session,
        data,
        created_by_id=payload.get("user_id") or payload.get("sub"),
    )
    await session.commit()
    return await service._to_job_response(session, job)
