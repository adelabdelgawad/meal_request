"""Meal Request Line Schemas."""

from datetime import datetime
from typing import Optional

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel


class MealRequestLineBase(CamelModel):
    meal_request_id: int
    employee_id: int
    attendance_time: Optional[datetime] = None
    shift_hours: Optional[int] = None
    is_accepted: bool = False
    notes: Optional[str] = Field(None, max_length=256)

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineCreate(CamelModel):
    """Schema for creating a meal request line."""
    meal_request_id: int
    employee_id: int
    attendance_time: Optional[datetime] = None
    shift_hours: Optional[int] = None
    is_accepted: bool = False
    notes: Optional[str] = Field(None, max_length=256)

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineUpdate(CamelModel):
    is_accepted: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=256)
    attendance_time: Optional[datetime] = None
    shift_hours: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineAttendanceResponse(CamelModel):
    """Nested attendance data for a meal request line (synced from TMS)."""
    attendance_in: Optional[datetime] = None
    attendance_out: Optional[datetime] = None
    working_hours: Optional[float] = None
    attendance_synced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineResponse(MealRequestLineBase):
    id: int
    created_at: datetime
    # Nested attendance data (synced from TMS)
    attendance: Optional[MealRequestLineAttendanceResponse] = None

    model_config = ConfigDict(from_attributes=True)
