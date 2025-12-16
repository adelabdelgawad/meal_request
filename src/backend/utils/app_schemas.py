from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict
from api.schemas._base import CamelModel

# Type variable for generic PaginatedResponse
T = TypeVar('T')


class PaginatedResponse(CamelModel, Generic[T]):
    """Generic paginated response schema with camelCase support."""

    items: List[T]
    total: int
    skip: int
    limit: int
    active_count: Optional[int] = None
    inactive_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserAttributes(BaseModel):
    display_name: str
    telephone: Optional[str] = None
    mail: Optional[str] = None
    title: Optional[str] = None


class MealRequestSummary(CamelModel):
    meal_request_id: int
    status_id: int
    status_name_en: str
    status_name_ar: str
    requester_name: str
    requester_title: Optional[str] = None
    notes: Optional[str]
    request_time: datetime
    closed_time: Optional[datetime]
    meal_type_en: Optional[str] = None
    meal_type_ar: Optional[str] = None
    total_request_lines: int
    accepted_request_lines: Optional[int]


class MealRequestLineRequest(CamelModel):
    """Request schema for creating meal request lines - employee_code is auto-populated."""
    employee_id: int
    # employee_code is auto-populated from employee record
    notes: Optional[str] = None


class MealRequestResponse(CamelModel):
    meal_request_id: int
    requester_name: str
    request_time: datetime
    request_notes: Optional[str] = None
    total_request_lines: Optional[int] = None
    accepted_request_lines: Optional[int] = None
    status_name: str
    close_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(CamelModel):
    username: str
    password: str

    model_config = ConfigDict(from_attributes=True)


class TmsAttendanceResponse(CamelModel):
    """TMS attendance data synced from the attendance system."""
    attendance_in: Optional[datetime] = None
    attendance_out: Optional[datetime] = None
    working_hours: Optional[float] = None
    attendance_synced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineResponse(CamelModel):
    request_line_id: int
    code: int
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    title: Optional[str] = None
    department_en: Optional[str] = None
    department_ar: Optional[str] = None
    shift_hours: Optional[int] = None
    sign_in_time: Optional[datetime] = None
    accepted: Optional[bool] = True
    notes: Optional[str] = None
    meal_type: Optional[str] = None
    # TMS attendance data (synced from attendance system)
    tms_attendance: Optional[TmsAttendanceResponse] = None


class RequestDataResponse(CamelModel):
    name: str
    accepted_requests: int

    model_config = ConfigDict(from_attributes=True)


class RequestsPageRecord(CamelModel):
    id: Optional[int]
    code: Optional[int] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    title: Optional[str] = None
    department_en: Optional[str] = None
    department_ar: Optional[str] = None


class RolePermissionResponse(CamelModel):
    username: Optional[str]
    role_ids: List[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreateRequest(CamelModel):
    created_by: int
    username: str
    role_ids: List[int]

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(CamelModel):
    role_ids: List[int]

    model_config = ConfigDict(from_attributes=True)


class UpdateUserPermissionRequest(CamelModel):
    requester_id: str = None  # UUID as string
    username: str
    added_roles: Optional[List[str]] = None  # UUIDs as strings
    removed_roles: Optional[List[str]] = None  # UUIDs as strings

    model_config = ConfigDict(from_attributes=True)


# Backward compatibility alias
UpdateAccountPermissionRequest = UpdateUserPermissionRequest


class AuditRecordRequest(CamelModel):
    """Audit record schema with bilingual fields (following app convention)."""
    code: Optional[int] = None  # Employee code
    employee_name_en: Optional[str] = None  # Employee name in English
    employee_name_ar: Optional[str] = None  # Employee name in Arabic
    title: Optional[str] = None  # Employee title
    department_en: Optional[str] = None  # Department name in English
    department_ar: Optional[str] = None  # Department name in Arabic
    requester_en: Optional[str] = None  # Requester name in English
    requester_ar: Optional[str] = None  # Requester name in Arabic
    requester_title: Optional[str] = None
    meal_type_en: Optional[str] = None  # Meal type in English
    meal_type_ar: Optional[str] = None  # Meal type in Arabic
    notes: Optional[str] = None
    request_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditRecordResponse(AuditRecordRequest):
    """Audit response with attendance data."""
    in_time: Optional[datetime] = None
    out_time: Optional[datetime] = None
    working_hours: Optional[float] = None
    # TMS attendance data (synced from attendance system)
    tms_attendance: Optional[TmsAttendanceResponse] = None


class Attendance(CamelModel):
    code: Optional[int]
    in_time: Optional[datetime]
    out_time: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class DomainUser(CamelModel):
    username: str
    email: Optional[str] = None
    fullName: Optional[str] = None
    title: Optional[str] = None
    office: Optional[str] = None
    phone: Optional[str] = None
    manager: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Backward compatibility alias
DomainAccount = DomainUser


class UpdateMealRequestLineRequest(CamelModel):
    """Request model for updating meal request line status and notes."""

    user_id: str  # UUID as string
    meal_request_line_id: int
    accepted: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
