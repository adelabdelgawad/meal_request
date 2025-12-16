"""Meal Request Schemas."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from api.schemas._base import CamelModel


class MealRequestBase(CamelModel):
    requester_id: UUID
    status_id: int
    meal_type_id: int
    closed_by_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=256)

    model_config = ConfigDict(from_attributes=True)


class MealRequestCreate(CamelModel):
    requester_id: str = Field(description="UUID of the requester")
    meal_type_id: int = Field(description="Type of meal")
    notes: Optional[str] = Field(None, max_length=256, description="Optional notes")

    model_config = ConfigDict(from_attributes=True)


class MealRequestUpdate(CamelModel):
    status_id: Optional[int] = None
    closed_by_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=256)
    closed_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestResponse(MealRequestBase):
    id: int
    request_time: datetime
    closed_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestListResponse(CamelModel):
    """Schema for listing meal requests with summary information."""
    meal_request_id: int
    requester_name: str
    requester_title: Optional[str] = None
    request_time: datetime
    closed_time: Optional[datetime] = None
    notes: Optional[str] = None
    meal_type: str  # meal type name, not ID
    total_request_lines: int
    accepted_request_lines: int
    status_name: Literal["Pending", "Approved", "Rejected"]
    status_id: int

    model_config = ConfigDict(from_attributes=True)


class RequestLineDetailResponse(CamelModel):
    """Schema for request line details with joined employee/department data."""
    request_line_id: int
    code: str  # employee code as string
    name_en: Optional[str] = None  # employee name in English
    name_ar: Optional[str] = None  # employee name in Arabic
    title: Optional[str] = None
    department_en: Optional[str] = None  # department name in English
    department_ar: Optional[str] = None  # department name in Arabic
    shift_hours: Optional[str] = None
    sign_in_time: Optional[str] = None
    meal_type: str  # meal type name
    accepted: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditRecordResponse(CamelModel):
    """Schema for audit report with full employee and requester information."""
    code: str  # employee code
    employee_name_en: Optional[str] = None
    employee_name_ar: Optional[str] = None
    title: Optional[str] = None
    department_en: Optional[str] = None
    department_ar: Optional[str] = None
    requester_en: Optional[str] = None  # requester name in English
    requester_ar: Optional[str] = None  # requester name in Arabic
    requester_title: Optional[str] = None
    request_time: datetime
    meal_type: str  # meal type name
    in_time: Optional[str] = None
    out_time: Optional[str] = None
    working_hours: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineCreate(CamelModel):
    """Schema for creating a meal request line."""
    employee_id: int
    employee_code: str
    department_id: int
    notes: Optional[str] = ""

    model_config = ConfigDict(from_attributes=True)


class CreateMealRequestBody(CamelModel):
    """Schema for creating a meal request with multiple lines."""
    request_lines: List[MealRequestLineCreate]

    model_config = ConfigDict(from_attributes=True)


class EmployeeWithDepartment(CamelModel):
    """Schema for employee data grouped with department information."""
    id: int
    code: str
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    title: Optional[str] = None
    department_id: int
    department_en: Optional[str] = None  # department name in English
    department_ar: Optional[str] = None  # department name in Arabic

    model_config = ConfigDict(from_attributes=True)


class MealRequestStatusUpdateResponse(CamelModel):
    """Response schema for meal request status update."""
    message: str
    meal_request_id: int
    status_id: int
    closed_by_id: Optional[str] = None
    closed_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestCreateResponse(CamelModel):
    """Response schema for meal request creation."""
    message: str
    meal_request_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CopyMealRequestResponse(CamelModel):
    """Response schema for copying a meal request."""
    message: str
    original_request_id: int
    new_meal_request_id: int
    lines_copied: int
    meal_type_id: int

    model_config = ConfigDict(from_attributes=True)
