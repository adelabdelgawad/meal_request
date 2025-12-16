"""
HRIS Endpoints - External HRIS/TMS data access for attendance and shifts.

These endpoints query the external HRIS database directly for real-time data.
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import HRISAttendanceResponse, HRISShiftResponse
from api.services.hris_service import HRISService
from core.exceptions import ValidationError
from db.hris_database import get_hris_session
from utils.security import require_admin, require_ordertaker_or_admin

router = APIRouter(prefix="/hris", tags=["hris"])


@router.get("/attendance", response_model=List[HRISAttendanceResponse])
async def get_hris_attendance(
    employee_code: int = Query(..., description="Employee code to query"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hris_session: AsyncSession = Depends(get_hris_session),
    _: None = Depends(require_ordertaker_or_admin),
):
    """
    Get attendance records for an employee within a date range.

    Requires: OrderTaker or Admin role

    Only returns records where the employee is currently ON SHIFT:
    - Excludes records where out time is >= ATTENDANCE_MIN_SHIFT_HOURS after in time
    - For records with invalid out (< ATTENDANCE_MIN_SHIFT_HOURS), out time is set to null
    """
    service = HRISService()
    try:
        records = await service.get_attendance_on_shift(
            hris_session, employee_code, start_date, end_date
        )

        if not records:
            return []

        # Convert to response schema
        return [
            HRISAttendanceResponse(
                employee_code=r.employee_code,
                time_in=r.time_in,
                time_out=r.time_out,
                attendance_date=r.time_in.date() if r.time_in else start_date,
            )
            for r in records
        ]
    except ValidationError:
        raise


@router.get("/attendance/raw", response_model=List[HRISAttendanceResponse])
async def get_hris_attendance_raw(
    employee_code: int = Query(..., description="Employee code to query"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hris_session: AsyncSession = Depends(get_hris_session),
    _: None = Depends(require_admin),
):
    """
    Get raw attendance records without filtering (for debugging/admin).

    Requires: Admin role

    Returns all attendance records including completed shifts.
    """
    service = HRISService()
    try:
        records = await service.get_attendance_raw(
            hris_session, employee_code, start_date, end_date
        )

        if not records:
            return []

        # Convert to response schema
        return [
            HRISAttendanceResponse(
                employee_code=r.employee_code,
                time_in=r.time_in,
                time_out=r.time_out,
                attendance_date=r.time_in.date() if r.time_in else start_date,
            )
            for r in records
        ]
    except ValidationError:
        raise


@router.get("/shifts", response_model=List[HRISShiftResponse])
async def get_hris_shifts(
    employee_id: int = Query(..., description="Employee ID in HRIS"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    hris_session: AsyncSession = Depends(get_hris_session),
    _: None = Depends(require_ordertaker_or_admin),
):
    """
    Get shift assignments for an employee within a date range.

    Requires: OrderTaker or Admin role
    """
    service = HRISService()
    try:
        shifts = await service.get_employee_shifts(
            hris_session, employee_id, start_date, end_date
        )

        if not shifts:
            return []

        # Convert to response schema
        return [
            HRISShiftResponse(
                id=s.id,
                employee_id=s.employee_id,
                duration_hours=s.duration_hours,
                date_from=s.date_from,
                shift_type=s.shift_type,
            )
            for s in shifts
        ]
    except ValidationError:
        raise
