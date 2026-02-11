"""
Reporting & Audit Endpoints - Generate audit reports and attendance records.
"""

import logging
import traceback
from datetime import datetime
from typing import List, Optional

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import join, select

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from api.services import MealRequestService
from db.model import (
    Department,
    Employee,
    MealRequest,
    MealRequestLine,
    MealRequestLineAttendance,
    MealType,
    User,
)
from utils.app_schemas import AuditRecordResponse
from utils.security import require_auditor_or_admin

# Initialize logger and timezone
logger = logging.getLogger(__name__)
cairo_tz = pytz.timezone("Africa/Cairo")

# Define API router
router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize services
meal_request_service = MealRequestService(session)


async def get_audit_records_count(
    session: AsyncSession,
    start_time: datetime,
    end_time: datetime,
    search: Optional[str] = None,
) -> int:
    """
    Get total count of audit records (without pagination).

    Args:
        session: Database session
        start_time: Start time for audit period
        end_time: End time for audit period
        search: Search term to filter by employee name, code, or department

    Returns:
        Total count of records matching the filters
    """
    from sqlalchemy import func

    # Count query (no joins needed for count)
    count_stmt = (
        select(func.count(MealRequestLine.id))
        .select_from(
            join(
                MealRequestLine,
                Employee,
                MealRequestLine.employee_id == Employee.id,
            )
        )
        .join(Department, Employee.department_id == Department.id)
        .join(MealRequest, MealRequestLine.meal_request_id == MealRequest.id)
        .where(
            MealRequestLine.is_accepted,  # Only accepted lines
            MealRequestLine.is_deleted == False,  # noqa: E712 - Exclude soft-deleted lines
            MealRequest.is_deleted == False,  # noqa: E712 - Exclude soft-deleted requests
            MealRequest.status_id == 2,  # Closed status
            MealRequest.request_time.between(start_time, end_time),
        )
    )

    # Add search filter if provided
    if search:
        search_filter = (
            Employee.name_en.ilike(f"%{search}%")
            | Employee.name_ar.ilike(f"%{search}%")
            | Employee.code.ilike(f"%{search}%")
            | Department.name_en.ilike(f"%{search}%")
            | Department.name_ar.ilike(f"%{search}%")
        )
        count_stmt = count_stmt.where(search_filter)

    try:
        result = await session.execute(count_stmt)
        total = result.scalar_one()
        return total
    except Exception as e:
        logger.error(f"Failed to count audit records: {e}")
        return 0


async def get_audit_records_with_attendance(
    session: AsyncSession,
    start_time: datetime,
    end_time: datetime,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
) -> tuple[List[AuditRecordResponse], int]:
    """
    Get audit records with attendance data from local database.
    Returns bilingual fields (EN and AR) for client-side language selection.

    Args:
        session: Database session
        start_time: Start time for audit period
        end_time: End time for audit period
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 10)
        search: Search term to filter by employee name, code, or department

    Returns:
        Tuple of (records list, total count)
    """
    # Get total count first
    total = await get_audit_records_count(session, start_time, end_time, search)
    # Query to get meal request lines with attendance data
    stmt = (
        select(
            MealRequestLine.id.label("line_id"),
            Employee.code.label("employee_code"),
            Employee.name_en.label("employee_name_en"),
            Employee.name_ar.label("employee_name_ar"),
            Employee.title.label("employee_title"),
            Department.name_en.label("department_en"),
            Department.name_ar.label("department_ar"),
            User.full_name.label("requester_name"),  # TODO: Add requester_name_ar when available
            User.title.label("requester_title"),
            MealType.name_en.label("meal_type_en"),
            MealType.name_ar.label("meal_type_ar"),
            MealRequestLine.notes.label("line_notes"),
            MealRequest.request_time.label("meal_request_time"),
            MealRequestLine.attendance_time.label("sign_in_time"),
            MealRequestLine.shift_hours.label("shift_hours"),
            MealRequestLineAttendance.attendance_in.label("attendance_in"),
            MealRequestLineAttendance.attendance_out.label("attendance_out"),
            MealRequestLineAttendance.working_hours.label("working_hours"),
            MealRequestLineAttendance.attendance_synced_at.label(
                "attendance_synced_at"
            ),
        )
        .select_from(
            join(
                MealRequestLine,
                Employee,
                MealRequestLine.employee_id == Employee.id,
            )
        )
        .join(Department, Employee.department_id == Department.id)
        .join(MealRequest, MealRequestLine.meal_request_id == MealRequest.id)
        .join(User, MealRequest.requester_id == User.id)
        .join(MealType, MealRequest.meal_type_id == MealType.id)
        .outerjoin(
            MealRequestLineAttendance,
            MealRequestLine.id
            == MealRequestLineAttendance.meal_request_line_id,
        )
        .where(
            MealRequestLine.is_accepted,  # Only accepted lines
            MealRequestLine.is_deleted == False,  # noqa: E712 - Exclude soft-deleted lines
            MealRequest.is_deleted == False,  # noqa: E712 - Exclude soft-deleted requests
            MealRequest.status_id == 2,  # Assuming 2 is the closed status
            MealRequest.request_time.between(start_time, end_time),
        )
        .order_by(MealRequest.request_time)
    )

    # Add search filter if provided
    if search:
        search_filter = (
            Employee.name_en.ilike(f"%{search}%")
            | Employee.name_ar.ilike(f"%{search}%")
            | Employee.code.ilike(f"%{search}%")
            | Department.name_en.ilike(f"%{search}%")
            | Department.name_ar.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    # Add pagination (limit defaults to 10)
    stmt = stmt.offset(skip).limit(limit)

    try:
        result = await session.execute(stmt)
        records = result.fetchall()

        # Convert to AuditRecordResponse objects with language-resolved fields
        audit_records = []
        for record in records:
            # Build TMS attendance data if available
            tms_attendance = None
            if record.attendance_in or record.attendance_out:
                from utils.app_schemas import TmsAttendanceResponse

                tms_attendance = TmsAttendanceResponse(
                    attendance_in=record.attendance_in,
                    attendance_out=record.attendance_out,
                    working_hours=record.working_hours,
                    attendance_synced_at=record.attendance_synced_at,
                )

            # Return bilingual fields - client will select based on locale
            audit_record = AuditRecordResponse(
                code=record.employee_code,
                employee_name_en=record.employee_name_en,
                employee_name_ar=record.employee_name_ar,
                title=record.employee_title,
                department_en=record.department_en,
                department_ar=record.department_ar,
                requester_en=record.requester_name,  # TODO: Add Arabic version when available
                requester_ar=record.requester_name,  # Using same for now
                requester_title=record.requester_title,
                meal_type_en=record.meal_type_en,
                meal_type_ar=record.meal_type_ar,
                notes=record.line_notes,
                request_time=record.meal_request_time,
                in_time=record.attendance_in,
                out_time=record.attendance_out,
                working_hours=record.working_hours,
                tms_attendance=tms_attendance,
            )
            audit_records.append(audit_record)

        return audit_records, total
    except Exception as e:
        logger.error(f"Failed to get audit records with attendance: {e}")
        raise


@router.get("/audit")
async def read_audit_records(
    start_time: datetime,
    end_time: datetime,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, description="Max records to return (default: 10)"),
    search: Optional[str] = Query(
        None, description="Search by employee name, code, or department"
    ),
    session: SessionDep,
    payload: dict = Depends(require_auditor_or_admin),
) -> dict:
    """
    Retrieve audit records with employee attendance data from local database.
    Requires Auditor or Admin role.

    Args:
        start_time: Start time for audit period
        end_time: End time for audit period
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 10)
        search: Optional search term to filter records
        session: Main database session
        payload: Authentication payload

    Returns:
        Paginated response with audit records and metadata:
        {
            "data": [AuditRecordResponse, ...],
            "total": int,
            "skip": int,
            "limit": int
        }
    """
    try:
        records, total = await get_audit_records_with_attendance(
            session, start_time, end_time, skip, limit, search
        )

        # Return paginated response
        return {
            "data": records,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while generating audit report.",
        )


# Frontend-compatible analytics endpoint (deprecated - use /audit instead)
@router.get("/analytics")
async def get_analytics_data(
    start_time: datetime,
    end_time: datetime,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, description="Max records to return (default: 10)"),
    search: Optional[str] = Query(
        None, description="Search by employee name, code, or department"
    ),
    session: SessionDep,
    payload: dict = Depends(require_auditor_or_admin),
) -> dict:
    """
    Frontend-compatible analytics endpoint (deprecated - use /audit instead).
    Requires Auditor or Admin role.

    Args:
        start_time: Start time for audit period
        end_time: End time for audit period
        skip: Number of records to skip (for pagination, default: 0)
        limit: Maximum number of records to return (default: 10)
        search: Optional search term to filter records
        session: Main database session
        payload: Authentication payload

    Returns:
        Paginated response with audit records and metadata
    """
    try:
        records, total = await get_audit_records_with_attendance(
            session, start_time, end_time, skip, limit, search
        )

        # Return paginated response
        return {
            "data": records,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while generating analytics data.",
        )
