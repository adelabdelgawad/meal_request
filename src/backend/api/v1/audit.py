"""
Audit Endpoints - Audit logging and tracking.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session
from api.schemas import (
    LogPermissionCreate,
    LogPermissionResponse,
    LogMealRequestLineCreate,
    LogMealRequestLineResponse,
    LogAuthenticationQuery,
    LogAuthenticationList,
    LogMealRequestQuery,
    LogMealRequestList,
    LogUserQuery,
    LogUserList,
    LogRoleQuery,
    LogRoleList,
    LogConfigurationQuery,
    LogConfigurationList,
    LogReplicationResponse,
)
from api.services import (
    LogPermissionService,
    LogMealRequestLineService,
    LogAuthenticationService,
    LogMealRequestService,
    LogUserService,
    LogRoleService,
    LogConfigurationService,
    LogReplicationService,
)
from core.exceptions import (
    NotFoundError,
    ValidationError,
    DatabaseError,
)
from utils.security import require_super_admin
from utils.audit_cleanup import cleanup_audit_logs, get_audit_log_statistics

router = APIRouter(prefix="/audit", tags=["audit"])


# Permission Log Endpoints
@router.post("/permissions", response_model=LogPermissionResponse, status_code=status.HTTP_201_CREATED)
async def log_permission_action(
    log_create: LogPermissionCreate,
    session: AsyncSession = Depends(get_session),
):
    """Internal use only - Log a permission action."""
    service = LogPermissionService()
    try:
        log = await service.log_permission_action(session,
            account_id=log_create.account_id,
            role_id=log_create.role_id,
            admin_id=log_create.admin_id,
            action=log_create.action,
            is_successful=log_create.is_successful,
            result=getattr(log_create, "result", None),
        )
        return log
    except (ValidationError, DatabaseError):
        raise



@router.get("/permissions/{log_id}", response_model=LogPermissionResponse)
async def get_permission_log(
    log_id: int,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Get a permission log by ID."""
    service = LogPermissionService()
    try:
        log = await service.get_log(session, log_id)
        return log
    except NotFoundError:
        raise


@router.get("/permissions", response_model=List[LogPermissionResponse])
async def list_permission_logs(
    page: int = 1,
    per_page: int = 25,
    account_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    action: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. List permission logs."""
    service = LogPermissionService()
    logs, total = await service.list_logs(session,
        page=page,
        per_page=per_page,
        account_id=account_id,
        admin_id=admin_id,
        action=action,
    )
    return logs


# Meal Request Line Log Endpoints
@router.post("/meal-requests", response_model=LogMealRequestLineResponse, status_code=status.HTTP_201_CREATED)
async def log_meal_request_action(
    log_create: LogMealRequestLineCreate, session: AsyncSession = Depends(get_session),
):
    """Internal use only - Log a meal request line action."""
    service = LogMealRequestLineService()
    try:
        log = await service.log_meal_request_action(session,
            meal_request_line_id=log_create.meal_request_line_id,
            account_id=log_create.account_id,
            action=log_create.action,
            is_successful=log_create.is_successful,
            result=getattr(log_create, "result", None),
        )
        return log
    except (ValidationError, DatabaseError):
        raise


@router.get("/meal-requests/{log_id}", response_model=LogMealRequestLineResponse)
async def get_meal_request_log(
    log_id: int,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. Get a meal request log by ID."""
    service = LogMealRequestLineService()
    try:
        log = await service.get_log(session, log_id)
        return log
    except NotFoundError:
        raise



@router.get("/meal-requests", response_model=List[LogMealRequestLineResponse])
async def list_meal_request_logs(
    page: int = 1,
    per_page: int = 25,
    meal_request_line_id: Optional[int] = None,
    account_id: Optional[int] = None,
    action: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Requires Super Admin role. List meal request logs."""
    service = LogMealRequestLineService()
    logs, total = await service.list_logs(session,
        page=page,
        per_page=per_page,
        meal_request_line_id=meal_request_line_id,
        account_id=account_id,
        action=action,
    )
    return logs


# ==================== NEW AUDIT SYSTEM ENDPOINTS ====================
# Authentication, Meal Request, User, Role, Configuration Logs


# ==================== Authentication Logs ====================

@router.get("/authentication", response_model=LogAuthenticationList)
async def query_authentication_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    is_successful: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Query authentication audit logs. Requires Super Admin role."""
    service = LogAuthenticationService()
    query_params = LogAuthenticationQuery(
        user_id=user_id,
        action=action,
        is_successful=is_successful,
        from_date=from_date,
        to_date=to_date,
    )
    return await service.query_logs(session, query_params, page, per_page)


@router.get("/authentication/{log_id}")
async def get_authentication_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get a single authentication audit log by ID. Requires Super Admin role."""
    service = LogAuthenticationService()
    log = await service.get_log(session, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Authentication log {log_id} not found"
        )
    return log


# ==================== Meal Request Logs (New System) ====================

@router.get("/meal-request-logs", response_model=LogMealRequestList)
async def query_meal_request_audit_logs(
    user_id: Optional[str] = None,
    meal_request_id: Optional[int] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Query meal request audit logs. Requires Super Admin role."""
    service = LogMealRequestService()
    query_params = LogMealRequestQuery(
        user_id=user_id,
        meal_request_id=meal_request_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
    )
    return await service.query_logs(session, query_params, page, per_page)


@router.get("/meal-request-logs/{log_id}")
async def get_meal_request_audit_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get a single meal request audit log by ID. Requires Super Admin role."""
    service = LogMealRequestService()
    log = await service.get_log(session, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meal request log {log_id} not found"
        )
    return log


@router.get("/meal-request-logs/request/{meal_request_id}")
async def get_meal_request_history(
    meal_request_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get audit history for a specific meal request. Requires Super Admin role."""
    service = LogMealRequestService()
    return await service.get_logs_for_meal_request(session, meal_request_id, page, per_page)


# ==================== User Management Logs ====================

@router.get("/user-logs", response_model=LogUserList)
async def query_user_audit_logs(
    admin_id: Optional[str] = None,
    target_user_id: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Query user management audit logs. Requires Super Admin role."""
    service = LogUserService()
    query_params = LogUserQuery(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
    )
    return await service.query_logs(session, query_params, page, per_page)


@router.get("/user-logs/{log_id}")
async def get_user_audit_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get a single user management audit log by ID. Requires Super Admin role."""
    service = LogUserService()
    log = await service.get_log(session, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User log {log_id} not found"
        )
    return log


@router.get("/user-logs/target/{target_user_id}")
async def get_user_history(
    target_user_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get audit history for a specific user. Requires Super Admin role."""
    service = LogUserService()
    return await service.get_by_target_user(session, target_user_id, page, per_page)


# ==================== Role Management Logs ====================

@router.get("/role-logs", response_model=LogRoleList)
async def query_role_audit_logs(
    admin_id: Optional[str] = None,
    role_id: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Query role management audit logs. Requires Super Admin role."""
    service = LogRoleService()
    query_params = LogRoleQuery(
        admin_id=admin_id,
        role_id=role_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
    )
    return await service.query_logs(session, query_params, page, per_page)


@router.get("/role-logs/{log_id}")
async def get_role_audit_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get a single role management audit log by ID. Requires Super Admin role."""
    service = LogRoleService()
    log = await service.get_log(session, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role log {log_id} not found"
        )
    return log


# ==================== Configuration Logs ====================

@router.get("/configuration-logs", response_model=LogConfigurationList)
async def query_configuration_audit_logs(
    admin_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Query configuration change audit logs. Requires Super Admin role."""
    service = LogConfigurationService()
    query_params = LogConfigurationQuery(
        admin_id=admin_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
    )
    return await service.query_logs(session, query_params, page, per_page)


@router.get("/configuration-logs/{log_id}")
async def get_configuration_audit_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get a single configuration audit log by ID. Requires Super Admin role."""
    service = LogConfigurationService()
    log = await service.get_log(session, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration log {log_id} not found"
        )
    return log


# ==================== Replication Logs ====================

@router.get("/replication-logs", response_model=List[LogReplicationResponse])
async def query_replication_audit_logs(
    operation_type: Optional[str] = None,
    is_successful: Optional[bool] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Query replication audit logs. Requires Super Admin role."""
    service = LogReplicationService()
    logs, total = await service.query_logs(
        session=session,
        operation_type=operation_type,
        is_successful=is_successful,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page,
    )
    return logs


@router.get("/replication-logs/{log_id}", response_model=LogReplicationResponse)
async def get_replication_audit_log(
    log_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """Get a single replication audit log by ID. Requires Super Admin role."""
    service = LogReplicationService()
    log = await service.get_log(session, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replication log {log_id} not found"
        )
    return log


# ==================== Cleanup & Statistics ====================

@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def manual_audit_cleanup(
    retention_days: int = Query(60, ge=1, le=365, description="Number of days to retain"),
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """
    Manually trigger audit log cleanup.
    Deletes logs older than retention_days (default: 60 days / 2 months).
    Requires Super Admin role.
    """
    try:
        result = await cleanup_audit_logs(session, retention_days)
        total_deleted = sum(result.values())

        return {
            "success": True,
            "message": f"Audit logs cleaned up successfully. Deleted {total_deleted} total records.",
            "retention_days": retention_days,
            "deleted_counts": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cleanup failed: {str(e)}"
        )


@router.get("/statistics", status_code=status.HTTP_200_OK)
async def get_audit_statistics(
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_super_admin),
):
    """
    Get audit log statistics (table sizes, oldest/newest timestamps).
    Requires Super Admin role.
    """
    try:
        stats = await get_audit_log_statistics(session)

        total_records = sum(
            table_stats.get("total_count", 0)
            for table_stats in stats.values()
        )

        return {
            "success": True,
            "total_records": total_records,
            "tables": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )