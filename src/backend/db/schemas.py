from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

# -------------------
# PagePermission Schemas
# -------------------


class PagePermissionBaseModel(BaseModel):
    role_id: Optional[int] = None
    page_id: Optional[int] = None
    created_by_id: Optional[str] = None  # UUID as string

    model_config = ConfigDict(from_attributes=True)


class PagePermission(PagePermissionBaseModel):
    id: int


class PagePermissionCreate(PagePermissionBaseModel):
    pass


# -------------------
# Page Schemas
# -------------------


class PageBaseModel(BaseModel):
    name_en: str
    name_ar: str
    description_en: Optional[str] = None
    description_ar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Page(PageBaseModel):
    id: int
    # Computed fields for backward compatibility (populated by API layer)
    name: Optional[str] = None
    description: Optional[str] = None


class PageCreate(PageBaseModel):
    # Accept legacy name field for backward compatibility
    name: Optional[str] = None

    def model_post_init(self, __context):
        """Map legacy name to bilingual fields if provided."""
        if self.name and not self.name_en:
            self.name_en = self.name
        if self.name and not self.name_ar:
            self.name_ar = self.name


class PageUpdate(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    # Accept legacy name field for backward compatibility
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context):
        """Map legacy name to bilingual fields if provided."""
        if self.name and not self.name_en:
            self.name_en = self.name
        if self.name and not self.name_ar:
            self.name_ar = self.name


# -------------------
# Role Schemas
# -------------------


class RoleBaseModel(BaseModel):
    name_en: str
    name_ar: str
    description_en: Optional[str] = None
    description_ar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Role(RoleBaseModel):
    id: int
    is_active: bool = True
    # Computed fields for backward compatibility (populated by API layer)
    name: Optional[str] = None
    description: Optional[str] = None
    # User count (populated by API layer)
    total_users: Optional[int] = None


class RoleCreate(RoleBaseModel):
    # Accept legacy name field for backward compatibility
    name: Optional[str] = None

    def model_post_init(self, __context):
        """Map legacy name to bilingual fields if provided."""
        if self.name and not self.name_en:
            self.name_en = self.name
        if self.name and not self.name_ar:
            self.name_ar = self.name


class RoleUpdate(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
    # Accept legacy name field for backward compatibility
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context):
        """Map legacy name to bilingual fields if provided."""
        if self.name and not self.name_en:
            self.name_en = self.name
        if self.name and not self.name_ar:
            self.name_ar = self.name


# -------------------
# User Schemas
# -------------------


class SecurityUserBaseModel(BaseModel):
    user_name: Optional[str]
    is_deleted: Optional[bool] = False
    is_locked: Optional[bool] = False
    emp_id: Optional[int] = None  # EmpId from HRIS Security.User (links to HRIS Employee.ID)

    model_config = ConfigDict(from_attributes=True)


class SecurityUser(SecurityUserBaseModel):
    id: int


class SecurityUserCreate(SecurityUserBaseModel):
    pass


# -------------------
# User Schemas
# -------------------


class UserBaseModel(BaseModel):
    username: Optional[str]
    password: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    is_domain_user: Optional[bool] = True
    is_super_admin: Optional[bool] = False
    preferred_locale: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class User(UserBaseModel):
    id: str  # UUID as string


class UserCreate(UserBaseModel):
    pass


# -------------------
# Employee Schemas
# -------------------


class EmployeeBaseModel(BaseModel):
    code: Optional[int] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    title: Optional[str] = None
    is_active: Optional[bool] = True
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class Employee(EmployeeBaseModel):
    id: int
    code: int
    name_en: Optional[str] = None
    name_ar: Optional[str] = None


class EmployeeCreate(BaseModel):
    code: int
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    title: Optional[str] = None
    is_active: bool = True
    department_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------
# EmployeeShift Schemas (for HRIS TMS data)
# -------------------


class EmployeeShift(BaseModel):
    """Shift assignment record from TMS."""
    id: int
    employee_id: int
    duration_hours: int
    date_from: datetime
    shift_type: str

    model_config = ConfigDict(from_attributes=True)


# -------------------
# Department Schemas
# -------------------


class DepartmentBaseModel(BaseModel):
    id: Optional[int] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class Department(DepartmentBaseModel):
    id: int
    name_en: str
    name_ar: str


class DepartmentCreate(BaseModel):
    name_en: str
    name_ar: str
    parent_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# -------------------
# DepartmentAssignment Schemas
# -------------------


class DepartmentAssignmentBaseModel(BaseModel):
    department_id: Optional[int] = None
    user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentAssignment(DepartmentAssignmentBaseModel):
    id: int
    department_id: int
    user_id: str


class DepartmentAssignmentCreate(BaseModel):
    department_id: int
    user_id: str

    model_config = ConfigDict(from_attributes=True)


# -------------------
# MealRequest Schemas
# -------------------


class MealRequestBaseModel(BaseModel):
    requester_id: Optional[int]
    meal_type_id: Optional[int]
    status_id: Optional[int] = 1
    request_time: Optional[datetime] = None
    closed_by_id: Optional[int] = None
    notes: Optional[str] = None
    closed_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequest(MealRequestBaseModel):
    id: int


class MealRequestCreate(MealRequestBaseModel):
    pass


# -------------------
# MealRequestStatus Schemas
# -------------------


class MealRequestStatusBaseModel(BaseModel):
    name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class MealRequestStatus(MealRequestStatusBaseModel):
    id: int


class MealRequestStatusCreate(MealRequestStatusBaseModel):
    pass


# -------------------
# MealType Schemas
# -------------------


class MealTypeBaseModel(BaseModel):
    name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class MealType(MealTypeBaseModel):
    id: int


class MealTypeCreate(MealTypeBaseModel):
    pass


# -------------------
# MealRequestLine Schemas
# -------------------


class MealRequestLineBaseModel(BaseModel):
    employee_id: Optional[int] = None
    department_id: Optional[int] = None
    meal_request_id: Optional[int] = None

    attendance_time: Optional[datetime] = None
    shift_hours: Optional[int] = None
    notes: Optional[str] = None
    is_accepted: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)


class MealRequestLine(MealRequestLineBaseModel):
    id: Optional[int] = None


class MealRequestLineCreate(BaseModel):
    """Schema for creating a meal request line - department_id is auto-populated from employee."""
    employee_id: int  # Required
    meal_request_id: Optional[int] = None

    attendance_time: Optional[datetime] = None
    shift_hours: Optional[int] = None
    notes: Optional[str] = None
    is_accepted: Optional[bool] = True

    model_config = ConfigDict(from_attributes=True)


# -------------------
# Email Schemas
# -------------------


class EmailBaseModel(BaseModel):
    address: Optional[str]
    role_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class Email(EmailBaseModel):
    id: int


class EmailCreate(EmailBaseModel):
    pass


# -------------------
# EmailRole Schemas
# -------------------


class EmailRoleBaseModel(BaseModel):
    name: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class EmailRole(EmailRoleBaseModel):
    id: int


class EmailRoleCreate(EmailRoleBaseModel):
    pass


class RolePermissionBaseModel(BaseModel):
    role_id: Optional[int]
    user_id: Optional[str]  # UUID as string

    model_config = ConfigDict(from_attributes=True)


class RolePermission(RolePermissionBaseModel):
    id: int


class RolePermissionCreate(RolePermissionBaseModel):
    pass


# -------------------
# LogPermission Schemas
# -------------------


class LogPermissionBaseModel(BaseModel):
    user_id: str  # UUID as string
    role_id: str  # UUID as string
    admin_id: str  # UUID as string
    action: str
    result: Optional[str] = None
    is_successful: Optional[bool] = None
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LogPermissionCreate(LogPermissionBaseModel):
    pass


class LogPermission(LogPermissionBaseModel):
    id: int


# -------------------
# LogMealRequestLine Schemas
# -------------------


class LogMealRequestLineBaseModel(BaseModel):
    meal_request_line_id: int
    user_id: str  # UUID as string
    action: str
    result: Optional[str] = None
    is_successful: Optional[bool] = None
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LogMealRequestLineCreate(LogMealRequestLineBaseModel):
    pass


class LogMealRequestLine(LogMealRequestLineBaseModel):
    id: int


# -------------------
# AttendanceRecord Schemas (for TMS sync)
# -------------------


class AttendanceRecord(BaseModel):
    """Attendance record from TMS for a single employee on a specific date."""
    employee_id: int
    time_in: Optional[datetime] = None
    time_out: Optional[datetime] = None
    working_hours: Optional[float] = None  # Calculated from time_in/time_out

    model_config = ConfigDict(from_attributes=True)


# -------------------
# DepartmentAssignmentRecord Schemas (for HRIS sync)
# -------------------


class DepartmentAssignmentRecord(BaseModel):
    """Department assignment record from TMS_ForwardEdit for HRIS sync."""
    employee_id: int  # HRIS EmployeeID from TMS_ForwardEdit
    department_id: int  # OrgUnitID from TMS_ForwardEdit

    model_config = ConfigDict(from_attributes=True)


# -------------------
# MealRequestLineAttendance Schemas
# -------------------


class MealRequestLineAttendanceBaseModel(BaseModel):
    meal_request_line_id: Optional[int] = None
    employee_code: Optional[int] = None
    attendance_date: Optional[datetime] = None
    attendance_in: Optional[datetime] = None
    attendance_out: Optional[datetime] = None
    working_hours: Optional[float] = None
    attendance_synced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MealRequestLineAttendance(MealRequestLineAttendanceBaseModel):
    id: int


class MealRequestLineAttendanceCreate(MealRequestLineAttendanceBaseModel):
    meal_request_line_id: int
    employee_code: int
    attendance_date: datetime
