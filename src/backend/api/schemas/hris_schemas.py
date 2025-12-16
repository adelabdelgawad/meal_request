"""
HRIS API Schemas - Response models for HRIS attendance and shift endpoints.

All schemas use CamelModel for automatic camelCase JSON serialization.
"""

from datetime import date, datetime
from typing import Optional

from api.schemas._base import CamelModel


class HRISAttendanceResponse(CamelModel):
    """
    Attendance record for an employee currently ON SHIFT.

    Note: Only records where employee is still working are returned.
    Records with valid out (>= ATTENDANCE_MIN_SHIFT_HOURS) are excluded.
    """
    employee_code: int
    time_in: datetime  # Required - when employee started shift
    time_out: Optional[datetime] = None  # Always None (still on shift)
    attendance_date: date


class HRISShiftResponse(CamelModel):
    """
    Shift assignment record from TMS.
    """
    id: int
    employee_id: int
    duration_hours: int
    date_from: datetime
    shift_type: str
