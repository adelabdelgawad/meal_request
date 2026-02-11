from datetime import date, datetime, timezone
from decimal import Decimal
from typing import ClassVar, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, String, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlmodel import Field, Relationship, SQLModel

from utils.datetime_utils import utcnow


def utc_now() -> datetime:
    """Get current time in UTC timezone."""
    return datetime.now(timezone.utc)


class TableModel(SQLModel):
    pass


# -------------------
# Page & Permission Models
# -------------------


class PagePermission(TableModel, table=True):
    __tablename__: ClassVar[str] = "page_permission"

    id: int = Field(default=None, primary_key=True, index=True)
    role_id: int = Field(foreign_key="role.id")
    page_id: int = Field(foreign_key="page.id")
    created_by_id: str = Field(foreign_key="user.id", max_length=36)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    role: "Role" = Relationship(back_populates="page_permissions")
    page: "Page" = Relationship(back_populates="page_permissions")
    created_by: "User" = Relationship(back_populates="page_permissions_created")

    def __repr__(self):
        return (
            f"<PagePermission(id={self.id}, role_id={self.role_id}, "
            f"page_id={self.page_id}, created_by_id={self.created_by_id})>"
        )


class Page(TableModel, table=True):
    __tablename__: ClassVar[str] = "page"

    id: int = Field(default=None, primary_key=True, index=True)
    name_en: str = Field(max_length=64, index=True)
    name_ar: str = Field(max_length=64, index=True)
    description_en: Optional[str] = Field(default=None, max_length=256)
    description_ar: Optional[str] = Field(default=None, max_length=256)
    name: Optional[str] = Field(default=None, max_length=64)
    path: Optional[str] = Field(default=None, max_length=256)
    parent_id: Optional[int] = Field(
        default=None, foreign_key="page.id", ondelete="CASCADE", index=True
    )
    order: int = Field(default=100)
    is_menu_group: bool = Field(default=False)
    nav_type: Optional[str] = Field(default=None, max_length=32, index=True)
    show_in_nav: bool = Field(default=True, index=True)
    icon: Optional[str] = Field(default=None, max_length=64)
    open_in_new_tab: bool = Field(default=False)
    visible_when: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    key: Optional[str] = Field(default=None, max_length=128, unique=True, index=True)

    page_permissions: List["PagePermission"] = Relationship(back_populates="page")
    parent: Optional["Page"] = Relationship(
        back_populates="children", sa_relationship_kwargs={"remote_side": "Page.id"}
    )
    children: List["Page"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        if locale and locale.lower() == "ar":
            return self.name_ar
        return self.name_en

    def get_description(self, locale: Optional[str] = None) -> Optional[str]:
        if locale and locale.lower() == "ar":
            return self.description_ar
        return self.description_en

    def __repr__(self):
        return f"<Page(id={self.id}, key='{self.key}', name_en='{self.name_en}', name_ar='{self.name_ar}')>"


# -------------------
# Role Models
# -------------------


class Role(TableModel, table=True):
    __tablename__: ClassVar[str] = "role"

    id: int = Field(default=None, primary_key=True, index=True)
    name_en: str = Field(max_length=64, unique=True, index=True)
    name_ar: str = Field(max_length=64, index=True)
    description_en: Optional[str] = Field(default=None, max_length=256)
    description_ar: Optional[str] = Field(default=None, max_length=256)
    name: Optional[str] = Field(default=None, max_length=64)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    permission_logs_admin: List["LogPermission"] = Relationship(back_populates="role")
    page_permissions: List["PagePermission"] = Relationship(back_populates="role")
    role_permissions: List["RolePermission"] = Relationship(back_populates="role")

    def get_name(self, locale: Optional[str] = None) -> str:
        if locale and locale.lower() == "ar":
            return self.name_ar
        return self.name_en

    def get_description(self, locale: Optional[str] = None) -> Optional[str]:
        if locale and locale.lower() == "ar":
            return self.description_ar
        return self.description_en

    def __repr__(self):
        return (
            f"<Role(id={self.id}, name_en='{self.name_en}', name_ar='{self.name_ar}')>"
        )


class RolePermission(TableModel, table=True):
    __tablename__: ClassVar[str] = "role_permission"

    id: int = Field(default=None, primary_key=True, index=True)
    role_id: int = Field(foreign_key="role.id")
    user_id: str = Field(foreign_key="user.id", max_length=36)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    role: "Role" = Relationship(back_populates="role_permissions")
    user: "User" = Relationship(back_populates="role_permissions")

    def __repr__(self):
        return (
            f"<RolePermission(id={self.id}, role_id={self.role_id}, "
            f"user_id={self.user_id})>"
        )


# -------------------
# Security & User Models
# -------------------


class SecurityUser(TableModel, table=True):
    __tablename__: ClassVar[str] = "security_user"

    id: int = Field(default=None, primary_key=True, index=True)
    user_name: str = Field(max_length=32)
    is_deleted: bool = Field()
    is_locked: bool = Field()
    employee_id: Optional[int] = Field(
        default=None,
        foreign_key="employee.id",
        ondelete="SET NULL",
        index=True,
    )

    employee: Optional["Employee"] = Relationship(back_populates="security_user")

    def __repr__(self):
        return (
            f"<SecurityUser(id={self.id}, user_name='{self.user_name}', "
            f"is_deleted={self.is_deleted}, is_locked={self.is_locked}, "
            f"employee_id={self.employee_id})>"
        )


class User(TableModel, table=True):
    __tablename__: ClassVar[str] = "user"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    username: str = Field(unique=True, max_length=64)
    email: Optional[str] = Field(default=None, unique=True, index=True, max_length=128)
    password: Optional[str] = Field(default=None, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=128)
    title: Optional[str] = Field(default=None, max_length=64)
    is_domain_user: bool = Field(default=True)
    is_super_admin: bool = Field(default=False)
    is_active: bool = Field(default=True, index=True)
    is_blocked: bool = Field(default=False, index=True)
    preferred_locale: Optional[str] = Field(default=None, max_length=2, index=True)
    employee_id: Optional[int] = Field(
        default=None,
        foreign_key="employee.id",
        ondelete="SET NULL",
        unique=True,
        index=True,
    )

    user_source: str = Field(
        default="hris",
        description="Source of user record: hris (synced from HRIS), manual (created by admin)",
    )
    status_override: bool = Field(
        default=False,
        description="If true, is_active status is manually controlled and HRIS sync will not modify it",
    )
    override_reason: Optional[str] = Field(
        default=None,
        description="Admin-provided reason for status override (required when override enabled)",
    )
    override_set_by_id: Optional[str] = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        description="User ID of admin who set the override",
    )
    override_set_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when override was enabled",
    )

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    meal_requests_requested: List["MealRequest"] = Relationship(
        back_populates="requester",
        sa_relationship_kwargs={"foreign_keys": "MealRequest.requester_id"},
    )
    meal_requests_closed: List["MealRequest"] = Relationship(
        back_populates="closed_by",
        sa_relationship_kwargs={"foreign_keys": "MealRequest.closed_by_id"},
    )
    page_permissions_created: List["PagePermission"] = Relationship(
        back_populates="created_by"
    )
    role_permissions: List["RolePermission"] = Relationship(back_populates="user")

    permission_logs_effected: List["LogPermission"] = Relationship(
        back_populates="effected_user",
        sa_relationship_kwargs={"foreign_keys": "LogPermission.user_id"},
    )
    permission_logs_admin: List["LogPermission"] = Relationship(
        back_populates="admin",
        sa_relationship_kwargs={"foreign_keys": "LogPermission.admin_id"},
    )
    meal_request_line_logs: List["LogMealRequestLine"] = Relationship(
        back_populates="user"
    )
    sessions: List["Session"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    department_assignments: List["DepartmentAssignment"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "DepartmentAssignment.user_id"},
    )
    meal_types_created: List["MealType"] = Relationship(
        back_populates="created_by",
        sa_relationship_kwargs={"foreign_keys": "MealType.created_by_id"},
    )
    meal_types_updated: List["MealType"] = Relationship(
        back_populates="updated_by",
        sa_relationship_kwargs={"foreign_keys": "MealType.updated_by_id"},
    )
    employee: Optional["Employee"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "User.employee_id", "uselist": False},
    )

    auth_logs: List["LogAuthentication"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogAuthentication.user_id"}
    )
    meal_request_logs: List["LogMealRequest"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogMealRequest.user_id"}
    )
    user_logs_as_admin: List["LogUser"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogUser.admin_id"}
    )
    user_logs_as_target: List["LogUser"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogUser.target_user_id"}
    )
    role_logs: List["LogRole"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogRole.admin_id"}
    )
    configuration_logs: List["LogConfiguration"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogConfiguration.admin_id"}
    )
    replication_logs: List["LogReplication"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "LogReplication.admin_id"}
    )
    employee: Optional["Employee"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "User.employee_id", "uselist": False},
    )

    def __repr__(self):
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"full_name='{self.full_name}', title='{self.title}', "
            f"is_domain_user={self.is_domain_user}, "
            f"is_super_admin={self.is_super_admin})>"
        )


# -------------------
# Employee & Department Models
# -------------------


class Employee(TableModel, table=True):
    __tablename__: ClassVar[str] = "employee"

    id: int = Field(
        default=None,
        primary_key=True,
        index=True,
        description="HRIS Employee ID - used as primary key for both internal and external system integration",
    )
    code: int = Field(unique=True)
    name_en: Optional[str] = Field(default=None, max_length=128)
    name_ar: Optional[str] = Field(default=None, max_length=128)
    title: Optional[str] = Field(default=None, max_length=128)
    is_active: bool = Field()
    department_id: Optional[int] = Field(default=None, foreign_key="department.id")

    department: Optional["Department"] = Relationship(back_populates="employees")
    meal_request_lines: List["MealRequestLine"] = Relationship(
        back_populates="employee"
    )
    security_user: Optional["SecurityUser"] = Relationship(back_populates="employee")
    user: Optional["User"] = Relationship(
        back_populates="employee",
        sa_relationship_kwargs={"foreign_keys": "User.employee_id", "uselist": False},
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        if locale and locale.lower() == "en":
            return self.name_en or ""
        return self.name_ar or ""

    def __repr__(self):
        return (
            f"<Employee(id={self.id}, code={self.code}, name_en='{self.name_en}', "
            f"name_ar='{self.name_ar}', title='{self.title}', is_active={self.is_active}, "
            f"department_id={self.department_id})>"
        )


class Department(TableModel, table=True):
    __tablename__: ClassVar[str] = "department"

    id: int = Field(default=None, primary_key=True, index=True)
    name_en: str = Field(max_length=128, index=True)
    name_ar: str = Field(max_length=128, index=True)
    parent_id: Optional[int] = Field(
        default=None, foreign_key="department.id", ondelete="SET NULL", index=True
    )

    employees: List["Employee"] = Relationship(back_populates="department")
    department_assignments: List["DepartmentAssignment"] = Relationship(
        back_populates="department"
    )
    parent: Optional["Department"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Department.id"},
    )
    children: List["Department"] = Relationship(back_populates="parent")

    def get_name(self, locale: Optional[str] = None) -> str:
        if locale and locale.lower() == "en":
            return self.name_en
        return self.name_ar

    def __repr__(self):
        return f"<Department(id={self.id}, name_en='{self.name_en}', name_ar='{self.name_ar}', parent_id={self.parent_id})>"


class DepartmentAssignment(TableModel, table=True):
    __tablename__: ClassVar[str] = "department_assignment"

    id: int = Field(default=None, primary_key=True, index=True)
    department_id: int = Field(foreign_key="department.id")
    user_id: str = Field(foreign_key="user.id", max_length=36)
    is_synced_from_hris: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    created_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", max_length=36
    )
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", max_length=36
    )

    department: "Department" = Relationship(back_populates="department_assignments")
    user: "User" = Relationship(
        back_populates="department_assignments",
        sa_relationship_kwargs={"foreign_keys": "DepartmentAssignment.user_id"},
    )
    created_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "DepartmentAssignment.created_by_id"}
    )
    updated_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "DepartmentAssignment.updated_by_id"}
    )

    def __repr__(self):
        return (
            f"<DepartmentAssignment(id={self.id}, department_id={self.department_id}, "
            f"user_id={self.user_id}, is_synced_from_hris={self.is_synced_from_hris}, "
            f"is_active={self.is_active})>"
        )


# -------------------
# Meal Request Models
# -------------------


class MealRequest(TableModel, table=True):
    __tablename__: ClassVar[str] = "meal_request"

    id: int = Field(default=None, primary_key=True, index=True)
    requester_id: str = Field(foreign_key="user.id", max_length=36)
    status_id: int = Field(foreign_key="meal_request_status.id")
    meal_type_id: int = Field(foreign_key="meal_type.id")
    request_time: datetime = Field(default_factory=utcnow)
    closed_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", max_length=36
    )
    notes: Optional[str] = Field(default=None, max_length=256)
    closed_time: Optional[datetime] = Field(default=None)
    original_request_id: Optional[int] = Field(
        default=None, foreign_key="meal_request.id", index=True
    )
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    requester: "User" = Relationship(
        back_populates="meal_requests_requested",
        sa_relationship_kwargs={"foreign_keys": "MealRequest.requester_id"},
    )
    closed_by: "User" = Relationship(
        back_populates="meal_requests_closed",
        sa_relationship_kwargs={"foreign_keys": "MealRequest.closed_by_id"},
    )
    status: "MealRequestStatus" = Relationship(back_populates="meal_requests")
    meal_type: "MealType" = Relationship(back_populates="meal_requests")
    meal_request_lines: List["MealRequestLine"] = Relationship(
        back_populates="meal_request"
    )
    original_request: Optional["MealRequest"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "MealRequest.id",
            "foreign_keys": "MealRequest.original_request_id",
        }
    )
    copies: List["MealRequest"] = Relationship(back_populates="original_request")
    copies: List["MealRequest"] = Relationship(back_populates="original_request")

    def __repr__(self):
        return (
            f"<MealRequest(id={self.id}, requester_id={self.requester_id}, "
            f"status_id={self.status_id}, meal_type_id={self.meal_type_id}, "
            f"request_time={self.request_time}, closed_by_id={self.closed_by_id}, "
            f"closed_time={self.closed_time})>"
        )


class MealRequestLine(TableModel, table=True):
    __tablename__: ClassVar[str] = "meal_request_line"

    id: int = Field(default=None, primary_key=True, index=True)
    employee_id: int = Field(foreign_key="employee.id")
    employee_code: Optional[int] = Field(default=None)
    meal_request_id: int = Field(foreign_key="meal_request.id")
    attendance_time: Optional[datetime] = Field(default=None)
    shift_hours: Optional[int] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=256)
    is_accepted: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    employee: "Employee" = Relationship(back_populates="meal_request_lines")
    meal_request: "MealRequest" = Relationship(back_populates="meal_request_lines")
    meal_request_line_logs: List["LogMealRequestLine"] = Relationship(
        back_populates="meal_request_line"
    )
    attendance: Optional["MealRequestLineAttendance"] = Relationship(
        back_populates="meal_request_line",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )

    def __repr__(self):
        return (
            f"<MealRequestLine(id={self.id}, employee_id={self.employee_id}, "
            f"meal_request_id={self.meal_request_id}, "
            f"shift_hours={self.shift_hours}, is_accepted={self.is_accepted})>"
        )


class MealRequestLineAttendance(TableModel, table=True):
    __tablename__: ClassVar[str] = "meal_request_line_attendance"

    id: int = Field(default=None, primary_key=True, index=True)
    meal_request_line_id: int = Field(
        foreign_key="meal_request_line.id", ondelete="CASCADE", unique=True, index=True
    )
    employee_code: int = Field(index=True)
    attendance_date: date = Field(index=True)
    attendance_in: Optional[datetime] = Field(default=None)
    attendance_out: Optional[datetime] = Field(default=None)
    working_hours: Optional[Decimal] = Field(default=None)
    attendance_synced_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    meal_request_line: "MealRequestLine" = Relationship(back_populates="attendance")

    def __repr__(self):
        return (
            f"<MealRequestLineAttendance(id={self.id}, "
            f"meal_request_line_id={self.meal_request_line_id}, "
            f"employee_code={self.employee_code}, "
            f"attendance_date={self.attendance_date}, "
            f"attendance_in={self.attendance_in}, "
            f"attendance_out={self.attendance_out}, "
            f"working_hours={self.working_hours})>"
        )


class MealRequestStatus(TableModel, table=True):
    __tablename__: ClassVar[str] = "meal_request_status"

    id: int = Field(default=None, primary_key=True, index=True)
    name_ar: str = Field(max_length=64)
    name_en: str = Field(max_length=64)
    is_active: bool = Field(default=True)

    meal_requests: List["MealRequest"] = Relationship(back_populates="status")

    def __repr__(self):
        return f"<MealRequestStatus(id={self.id}, name_ar='{self.name_ar}', name_en='{self.name_en}', is_active={self.is_active})>"


class MealType(TableModel, table=True):
    __tablename__: ClassVar[str] = "meal_type"

    id: int = Field(default=None, primary_key=True, index=True)
    name_en: str = Field(max_length=64, index=True)
    name_ar: str = Field(max_length=64, index=True)
    priority: int = Field(default=0, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    created_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", max_length=36
    )
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", max_length=36
    )
    is_active: bool = Field(default=True, index=True)
    is_deleted: bool = Field(default=False, index=True)

    meal_requests: List["MealRequest"] = Relationship(back_populates="meal_type")
    created_by: Optional["User"] = Relationship(
        back_populates="meal_types_created",
        sa_relationship_kwargs={"foreign_keys": "MealType.created_by_id"},
    )
    updated_by: Optional["User"] = Relationship(
        back_populates="meal_types_updated",
        sa_relationship_kwargs={"foreign_keys": "MealType.updated_by_id"},
    )

    def __repr__(self):
        return f"<MealType(id={self.id}, name_en='{self.name_en}', name_ar='{self.name_ar}', is_active={self.is_active})>"

    def get_name(self, locale: Optional[str] = None) -> str:
        if locale and locale.lower() == "en":
            return self.name_en or ""
        return self.name_ar or ""


# -------------------
# Email Models
# -------------------


class Email(TableModel, table=True):
    __tablename__: ClassVar[str] = "email"

    id: int = Field(default=None, primary_key=True, index=True)
    address: str = Field(unique=True, max_length=200)
    role_id: int = Field(foreign_key="email_role.id")

    role: "EmailRole" = Relationship(back_populates="emails")

    def __repr__(self):
        return (
            f"<Email(id={self.id}, address='{self.address}', role_id={self.role_id})>"
        )


class EmailRole(TableModel, table=True):
    __tablename__: ClassVar[str] = "email_role"

    id: int = Field(default=None, primary_key=True, index=True)
    name: str = Field(max_length=50)

    emails: List["Email"] = Relationship(back_populates="role")

    def __repr__(self):
        return f"<EmailRole(id={self.id}, name='{self.name}')>"


# -------------------
# Audit Log Models
# -------------------


class LogPermission(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_permission"

    id: int = Field(default=None, primary_key=True, index=True)
    user_id: str = Field(foreign_key="user.id", max_length=36)
    role_id: int = Field(foreign_key="role.id")
    admin_id: str = Field(foreign_key="user.id", max_length=36)
    action: str = Field(max_length=32)
    is_successful: bool = Field()
    result: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=utcnow)

    effected_user: "User" = Relationship(
        back_populates="permission_logs_effected",
        sa_relationship_kwargs={"foreign_keys": "LogPermission.user_id"},
    )
    admin: "User" = Relationship(
        back_populates="permission_logs_admin",
        sa_relationship_kwargs={"foreign_keys": "LogPermission.admin_id"},
    )
    role: "Role" = Relationship(back_populates="permission_logs_admin")

    def __repr__(self):
        return (
            f"<LogPermission(id={self.id}, user_id={self.user_id}, "
            f"admin_id={self.admin_id}, action='{self.action}', timestamp={self.timestamp})>"
        )


class LogMealRequestLine(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_meal_request_line"

    id: int = Field(default=None, primary_key=True, index=True)
    meal_request_line_id: int = Field(foreign_key="meal_request_line.id")
    user_id: str = Field(foreign_key="user.id", max_length=36)
    action: str = Field(max_length=32)
    is_successful: bool = Field()
    result: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=utcnow)

    meal_request_line: "MealRequestLine" = Relationship(
        back_populates="meal_request_line_logs"
    )
    user: "User" = Relationship(back_populates="meal_request_line_logs")

    def __repr__(self):
        return (
            f"<LogMealRequestLine(id={self.id}, meal_request_line_id={self.meal_request_line_id}, "
            f"user_id={self.user_id}, action='{self.action}', "
            f"timestamp={self.timestamp})>"
        )


class LogAuthentication(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_authentication"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    timestamp: datetime = Field(default_factory=utcnow)
    user_id: Optional[str] = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        index=True,
        max_length=36,
    )
    action: str = Field(max_length=64, index=True)
    is_successful: bool = Field()
    ip_address: Optional[str] = Field(default=None, max_length=64, index=True)
    user_agent: Optional[str] = Field(default=None)
    device_fingerprint: Optional[str] = Field(default=None, max_length=255)
    result: Optional[str] = Field(default=None)

    def __repr__(self):
        return (
            f"<LogAuthentication(id={self.id}, action='{self.action}', "
            f"user_id={self.user_id}, is_successful={self.is_successful}, "
            f"timestamp={self.timestamp})>"
        )


class LogMealRequest(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_meal_request"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    timestamp: datetime = Field(default_factory=utcnow)
    user_id: str = Field(
        foreign_key="user.id", ondelete="CASCADE", index=True, max_length=36
    )
    meal_request_id: Optional[int] = Field(
        default=None, foreign_key="meal_request.id", ondelete="SET NULL", index=True
    )
    action: str = Field(max_length=64, index=True)
    is_successful: bool = Field()
    old_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)
    result: Optional[str] = Field(default=None)

    meal_request: Optional["MealRequest"] = Relationship(back_populates="audit_logs")

    def __repr__(self):
        return (
            f"<LogMealRequest(id={self.id}, action='{self.action}', "
            f"meal_request_id={self.meal_request_id}, user_id={self.user_id}, "
            f"timestamp={self.timestamp})>"
        )


class LogUser(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_user"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    timestamp: datetime = Field(default_factory=utcnow)
    admin_id: str = Field(
        foreign_key="user.id", ondelete="CASCADE", index=True, max_length=36
    )
    target_user_id: Optional[str] = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        index=True,
        max_length=36,
    )
    action: str = Field(max_length=64, index=True)
    is_successful: bool = Field()
    old_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)
    result: Optional[str] = Field(default=None)

    def __repr__(self):
        return (
            f"<LogUser(id={self.id}, action='{self.action}', "
            f"admin_id={self.admin_id}, target_user_id={self.target_user_id}, "
            f"timestamp={self.timestamp})>"
        )

    def __repr__(self):
        return (
            f"<LogUser(id={self.id}, action='{self.action}', "
            f"admin_id={self.admin_id}, target_user_id={self.target_user_id}, "
            f"timestamp={self.timestamp})>"
        )


class LogRole(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_role"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    timestamp: datetime = Field(default_factory=utcnow)
    admin_id: str = Field(
        foreign_key="user.id", ondelete="CASCADE", index=True, max_length=36
    )
    role_id: Optional[int] = Field(
        default=None, foreign_key="role.id", ondelete="SET NULL", index=True
    )
    action: str = Field(max_length=64, index=True)
    is_successful: bool = Field()
    old_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)
    result: Optional[str] = Field(default=None)

    role: Optional["Role"] = Relationship(back_populates="audit_logs")

    def __repr__(self):
        return (
            f"<LogRole(id={self.id}, action='{self.action}', "
            f"admin_id={self.admin_id}, role_id={self.role_id}, "
            f"timestamp={self.timestamp})>"
        )


class LogConfiguration(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_configuration"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    timestamp: datetime = Field(default_factory=utcnow, index=True)
    admin_id: str = Field(
        foreign_key="user.id", ondelete="CASCADE", index=True, max_length=36
    )
    entity_type: str = Field(max_length=64, index=True)
    entity_id: Optional[str] = Field(default=None, max_length=36)
    action: str = Field(max_length=64, index=True)
    is_successful: bool = Field()
    old_value: Optional[str] = Field(default=None)
    new_value: Optional[str] = Field(default=None)
    result: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)

    __table_args__ = (Index("idx_log_config_entity", "entity_type", "entity_id"),)

    def __repr__(self):
        return (
            f"<LogConfiguration(id={self.id}, entity_type='{self.entity_type}', "
            f"entity_id={self.entity_id}, action='{self.action}', "
            f"created_at={self.created_at})>"
        )

    def __repr__(self):
        return (
            f"<LogConfiguration(id={self.id}, entity_type='{self.entity_type}', "
            f"entity_id={self.entity_id}, action='{self.action}', "
            f"created_at={self.created_at})>"
        )


class LogReplication(TableModel, table=True):
    __tablename__: ClassVar[str] = "log_replication"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    timestamp: datetime = Field(default_factory=utcnow, index=True)
    admin_id: Optional[str] = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        index=True,
        max_length=36,
    )
    operation_type: str = Field(max_length=64, index=True)
    is_successful: bool = Field()
    records_processed: Optional[int] = Field(default=None)
    records_created: Optional[int] = Field(default=None)
    records_updated: Optional[int] = Field(default=None)
    records_skipped: Optional[int] = Field(default=None)
    records_failed: Optional[int] = Field(default=None)
    source_system: Optional[str] = Field(default=None, max_length=64)
    duration_ms: Optional[int] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    result: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_log_replication_operation_timestamp", "operation_type", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<LogReplication(id={self.id}, operation_type='{self.operation_type}', "
            f"is_successful={self.is_successful}, "
            f"timestamp={self.timestamp})>"
        )

    def __repr__(self):
        return (
            f"<LogReplication(id={self.id}, operation_type='{self.operation_type}', "
            f"is_successful={self.is_successful}, "
            f"timestamp={self.timestamp})>"
        )


# -------------------
# Session & Token Models
# -------------------


class RevokedToken(TableModel, table=True):
    __tablename__: ClassVar[str] = "revoked_tokens"

    id: int = Field(default=None, primary_key=True, index=True)
    jti: str = Field(unique=True, index=True, max_length=64)
    token_type: str = Field(max_length=16)
    user_id: str = Field(foreign_key="user.id", max_length=36)
    revoked_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field()

    user: "User" = Relationship()

    def __repr__(self):
        return (
            f"<RevokedToken(id={self.id}, jti='{self.jti}', "
            f"token_type='{self.token_type}', user_id={self.user_id})>"
        )


class Session(TableModel, table=True):
    __tablename__: ClassVar[str] = "sessions"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True
    )
    user_id: str = Field(foreign_key="user.id", index=True, max_length=36)
    refresh_token_id: str = Field(unique=True, index=True, max_length=36)
    created_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field()
    revoked: bool = Field(default=False)
    device_info: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    fingerprint: Optional[str] = Field(default=None, max_length=255)
    session_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    user: "User" = Relationship(back_populates="sessions")

    def __repr__(self):
        return (
            f"<Session(id={self.id}, user_id={self.user_id}, "
            f"refresh_token_id={self.refresh_token_id}, revoked={self.revoked})>"
        )


class DomainUser(TableModel, table=True):
    __tablename__: ClassVar[str] = "domain_user"

    id: int = Field(default=None, primary_key=True, index=True)
    username: str = Field(unique=True, index=True, max_length=64)
    email: Optional[str] = Field(default=None, max_length=128, index=True)
    full_name: Optional[str] = Field(default=None, max_length=128)
    title: Optional[str] = Field(default=None, max_length=128)
    office: Optional[str] = Field(default=None, max_length=128)
    phone: Optional[str] = Field(default=None, max_length=32)
    manager: Optional[str] = Field(default=None, max_length=128)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def __repr__(self):
        return (
            f"<DomainUser(id={self.id}, username='{self.username}', "
            f"full_name='{self.full_name}')>"
        )


# -------------------
# Scheduler Models
# -------------------


class TaskFunction(TableModel, table=True):
    __tablename__: ClassVar[str] = "task_function"

    id: int = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True, max_length=64)
    function_path: str = Field(max_length=256)
    name_en: str = Field(max_length=128)
    name_ar: str = Field(max_length=128)
    description_en: Optional[str] = Field(default=None, max_length=512)
    description_ar: Optional[str] = Field(default=None, max_length=512)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    scheduled_jobs: List["ScheduledJob"] = Relationship(back_populates="task_function")

    def __repr__(self):
        return (
            f"<TaskFunction(id={self.id}, key='{self.key}', name_en='{self.name_en}')>"
        )


class SchedulerExecutionStatus(TableModel, table=True):
    __tablename__: ClassVar[str] = "scheduler_execution_status"

    id: int = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=32)
    name_en: str = Field(max_length=64)
    name_ar: str = Field(max_length=64)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    executions: List["ScheduledJobExecution"] = Relationship(
        back_populates="status_ref"
    )

    def __repr__(self):
        return f"<SchedulerExecutionStatus(id={self.id}, code='{self.code}', name_en='{self.name_en}')>"


class SchedulerJobType(TableModel, table=True):
    __tablename__: ClassVar[str] = "scheduler_job_type"

    id: int = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=32)
    name_en: str = Field(max_length=64)
    name_ar: str = Field(max_length=64)
    description_en: Optional[str] = Field(default=None, max_length=256)
    description_ar: Optional[str] = Field(default=None, max_length=256)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)

    scheduled_jobs: List["ScheduledJob"] = Relationship(back_populates="job_type_ref")

    def __repr__(self):
        return f"<SchedulerJobType(id={self.id}, code='{self.code}', name_en='{self.name_en}')>"


class ScheduledJob(TableModel, table=True):
    __tablename__: ClassVar[str] = "scheduled_job"

    id: int = Field(default=None, primary_key=True, index=True)
    task_function_id: int = Field(
        foreign_key="task_function.id", ondelete="RESTRICT", index=True
    )
    job_type_id: int = Field(
        foreign_key="scheduler_job_type.id", ondelete="RESTRICT", index=True
    )
    name_en: Optional[str] = Field(default=None, max_length=128)
    name_ar: Optional[str] = Field(default=None, max_length=128)
    description_en: Optional[str] = Field(default=None, max_length=512)
    description_ar: Optional[str] = Field(default=None, max_length=512)
    interval_seconds: Optional[int] = Field(default=None)
    interval_minutes: Optional[int] = Field(default=None)
    interval_hours: Optional[int] = Field(default=None)
    interval_days: Optional[int] = Field(default=None)
    cron_expression: Optional[str] = Field(default=None, max_length=64)
    priority: int = Field(default=0)
    max_instances: int = Field(default=1)
    misfire_grace_time: int = Field(default=300)
    coalesce: bool = Field(default=True)
    is_enabled: bool = Field(default=True, index=True)
    is_active: bool = Field(default=True, index=True)
    is_primary: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_run_at: Optional[datetime] = Field(default=None)
    created_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", max_length=36
    )
    updated_by_id: Optional[str] = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", max_length=36
    )

    task_function: "TaskFunction" = Relationship(back_populates="scheduled_jobs")
    job_type_ref: "SchedulerJobType" = Relationship(back_populates="scheduled_jobs")
    executions: List["ScheduledJobExecution"] = Relationship(
        back_populates="job", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    locks: List["ScheduledJobLock"] = Relationship(
        back_populates="job", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    created_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ScheduledJob.created_by_id"}
    )
    updated_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "ScheduledJob.updated_by_id"}
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        if locale and locale.lower() == "ar":
            return self.name_ar or (
                self.task_function.name_ar if self.task_function else ""
            )
        return self.name_en or (
            self.task_function.name_en if self.task_function else ""
        )

    def get_description(self, locale: Optional[str] = None) -> Optional[str]:
        if locale and locale.lower() == "ar":
            return self.description_ar or (
                self.task_function.description_ar if self.task_function else None
            )
        return self.description_en or (
            self.task_function.description_en if self.task_function else None
        )

    def __repr__(self):
        return (
            f"<ScheduledJob(id={self.id}, task_function_id={self.task_function_id}, "
            f"job_type_id={self.job_type_id}, is_enabled={self.is_enabled})>"
        )


class ScheduledJobExecution(TableModel, table=True):
    __tablename__: ClassVar[str] = "scheduled_job_execution"

    id: int = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="scheduled_job.id", ondelete="CASCADE", index=True)
    execution_id: str = Field(unique=True, index=True, max_length=36)
    run_id: Optional[str] = Field(default=None, max_length=64)
    scheduled_at: datetime = Field()
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    status_id: int = Field(
        foreign_key="scheduler_execution_status.id", ondelete="RESTRICT", index=True
    )
    error_message: Optional[str] = Field(default=None)
    error_traceback: Optional[str] = Field(default=None)
    result_summary: Optional[str] = Field(default=None, max_length=512)
    executor_id: Optional[str] = Field(default=None, max_length=128)
    host_name: Optional[str] = Field(default=None, max_length=128)
    created_at: datetime = Field(default_factory=utcnow, index=True)

    job: "ScheduledJob" = Relationship(back_populates="executions")
    status_ref: "SchedulerExecutionStatus" = Relationship(back_populates="executions")

    def __repr__(self):
        return (
            f"<ScheduledJobExecution(id={self.id}, job_id={self.job_id}, "
            f"status_id={self.status_id}, scheduled_at={self.scheduled_at})>"
        )


class ScheduledJobLock(TableModel, table=True):
    __tablename__: ClassVar[str] = "scheduled_job_lock"

    id: int = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="scheduled_job.id", ondelete="CASCADE")
    execution_id: str = Field(max_length=36)
    executor_id: str = Field(max_length=128)
    host_name: str = Field(max_length=128)
    acquired_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field()
    released_at: Optional[datetime] = Field(default=None)

    __table_args__ = (
        UniqueConstraint("job_id", "execution_id", name="uq_job_lock_job_execution"),
    )

    job: "ScheduledJob" = Relationship(back_populates="locks")

    def __repr__(self):
        return (
            f"<ScheduledJobLock(id={self.id}, job_id={self.job_id}, "
            f"executor_id='{self.executor_id}', expires_at={self.expires_at})>"
        )


class SchedulerInstance(TableModel, table=True):
    __tablename__: ClassVar[str] = "scheduler_instance"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    instance_name: str = Field(max_length=128)
    host_name: str = Field(max_length=128)
    process_id: int = Field()
    mode: str = Field(max_length=16)
    status: str = Field(max_length=16, index=True)
    last_heartbeat: datetime = Field(index=True)
    started_at: datetime = Field(default_factory=utcnow)
    stopped_at: Optional[datetime] = Field(default=None)

    def __repr__(self):
        return (
            f"<SchedulerInstance(id={self.id}, instance_name='{self.instance_name}', "
            f"mode='{self.mode}', status='{self.status}')>"
        )
