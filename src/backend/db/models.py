import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.mysql import CHAR, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Import datetime utilities for consistent UTC handling
from utils.datetime_utils import utcnow

# Base class using the new DeclarativeBase


class Base(DeclarativeBase):
    pass


# UUID type for MySQL/MariaDB (stored as CHAR(36))
def uuid_column(
    primary_key: bool = False, nullable: bool = False, index: bool = False
):
    """Create a UUID column compatible with MySQL/MariaDB."""
    return mapped_column(
        CHAR(36),
        primary_key=primary_key,
        nullable=nullable,
        index=index,
        default=lambda: str(uuid.uuid4()) if primary_key else None,
    )


# -------------------
# SQLAlchemy Models
# -------------------


class PagePermission(Base):
    __tablename__ = "page_permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id"), nullable=False
    )
    page_id: Mapped[int] = mapped_column(ForeignKey("page.id"), nullable=False)
    created_by_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    role: Mapped["Role"] = relationship(back_populates="page_permissions")
    page: Mapped["Page"] = relationship(back_populates="page_permissions")
    created_by: Mapped["User"] = relationship(
        back_populates="page_permissions_created"
    )

    def __repr__(self):
        return (
            f"<PagePermission(id={self.id}, role_id={self.role_id}, "
            f"page_id={self.page_id}, created_by_id={self.created_by_id})>"
        )


class Page(Base):
    __tablename__ = "page"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    name_ar: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    # Bilingual description fields
    description_en: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    description_ar: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    # Legacy name column (kept for backward compatibility during migration)
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Navigation fields
    path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("page.id", ondelete="CASCADE"), nullable=True, index=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_menu_group: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    nav_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    show_in_nav: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    icon: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    open_in_new_tab: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    visible_when: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    key: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )

    # Relationships
    page_permissions: Mapped[List["PagePermission"]] = relationship(
        back_populates="page"
    )
    # Self-referencing relationship for parent/children
    parent: Mapped[Optional["Page"]] = relationship(
        "Page", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Page"]] = relationship(
        "Page", back_populates="parent", cascade="all, delete-orphan"
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        """Get name for the specified locale (ar/en). Defaults to English."""
        if locale and locale.lower() == "ar":
            return self.name_ar
        return self.name_en

    def get_description(self, locale: Optional[str] = None) -> Optional[str]:
        """Get description for the specified locale (ar/en). Defaults to English."""
        if locale and locale.lower() == "ar":
            return self.description_ar
        return self.description_en

    def __repr__(self):
        return f"<Page(id={self.id}, key='{self.key}', name_en='{self.name_en}', name_ar='{self.name_ar}')>"


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )
    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    name_ar: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    # Bilingual description fields
    description_en: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    description_ar: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    # Legacy name column (kept for backward compatibility during migration)
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Active status flag
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    permission_logs_admin: Mapped[List["LogPermission"]] = relationship(
        back_populates="role"
    )
    page_permissions: Mapped[List["PagePermission"]] = relationship(
        back_populates="role"
    )
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        back_populates="role"
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        """Get name for the specified locale (ar/en). Defaults to English."""
        if locale and locale.lower() == "ar":
            return self.name_ar
        return self.name_en

    def get_description(self, locale: Optional[str] = None) -> Optional[str]:
        """Get description for the specified locale (ar/en). Defaults to English."""
        if locale and locale.lower() == "ar":
            return self.description_ar
        return self.description_en

    def __repr__(self):
        return f"<Role(id={self.id}, name_en='{self.name_en}', name_ar='{self.name_ar}')>"


class SecurityUser(Base):
    __tablename__ = "security_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_name: Mapped[str] = mapped_column(String(32), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Link to employee record from HRIS sync",
    )

    # Relationships
    employee: Mapped[Optional["Employee"]] = relationship(back_populates="security_user")

    def __repr__(self):
        return (
            f"<SecurityUser(id={self.id}, user_name='{self.user_name}', "
            f"is_deleted={self.is_deleted}, is_locked={self.is_locked}, "
            f"employee_id={self.employee_id})>"
        )


# In Account model
class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, unique=True, index=True
    )
    password: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )  # Increased to 128 for bcrypt hashes
    full_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_domain_user: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # Default True: all users are domain users except super admin
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    preferred_locale: Mapped[Optional[str]] = mapped_column(
        CHAR(2), nullable=True, index=True
    )
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employee.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
        comment="Link to employee record for HRIS sync",
    )

    # User Source Tracking and Status Override Fields (Strategy A - Simplified)
    user_source: Mapped[str] = mapped_column(
        Enum("hris", "manual", name="user_source_enum"),
        nullable=False,
        server_default="hris",
        comment="Source of user record: hris (synced from HRIS), manual (created by admin)",
    )
    status_override: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="0",
        comment="If true, is_active status is manually controlled and HRIS sync will not modify it",
    )
    override_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Admin-provided reason for status override (required when override enabled)",
    )
    override_set_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID of admin who set the override",
    )
    override_set_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when override was enabled",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Existing Relationships
    meal_requests_requested: Mapped[List["MealRequest"]] = relationship(
        back_populates="requester", foreign_keys="MealRequest.requester_id"
    )
    meal_requests_closed: Mapped[List["MealRequest"]] = relationship(
        back_populates="closed_by", foreign_keys="MealRequest.closed_by_id"
    )
    page_permissions_created: Mapped[List["PagePermission"]] = relationship(
        back_populates="created_by"
    )
    role_permissions: Mapped[List["RolePermission"]] = relationship(
        back_populates="user"
    )

    # New Logging Relationships
    permission_logs_effected: Mapped[List["LogPermission"]] = relationship(
        "LogPermission",
        foreign_keys="LogPermission.user_id",
        back_populates="effected_user",
    )
    permission_logs_admin: Mapped[List["LogPermission"]] = relationship(
        "LogPermission",
        foreign_keys="LogPermission.admin_id",
        back_populates="admin",
    )
    meal_request_line_logs: Mapped[List["LogMealRequestLine"]] = relationship(
        back_populates="user"
    )
    sessions: Mapped[List["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    department_assignments: Mapped[List["DepartmentAssignment"]] = (
        relationship(back_populates="user", foreign_keys="DepartmentAssignment.user_id")
    )
    meal_types_created: Mapped[List["MealType"]] = relationship(
        foreign_keys="MealType.created_by_id", back_populates="created_by"
    )
    meal_types_updated: Mapped[List["MealType"]] = relationship(
        foreign_keys="MealType.updated_by_id", back_populates="updated_by"
    )
    employee: Mapped[Optional["Employee"]] = relationship(
        "Employee",
        back_populates="user",
        foreign_keys="[User.employee_id]",
    )

    def __repr__(self):
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"full_name='{self.full_name}', title='{self.title}', "
            f"is_domain_user={self.is_domain_user}, "
            f"is_super_admin={self.is_super_admin})>"
        )


class Employee(Base):
    __tablename__ = "employee"

    # Primary key is the HRIS employee ID (not auto-increment)
    # This consolidates the previous dual-ID system (id + hris_id)
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=False,
        comment="HRIS Employee ID - used as primary key for both internal and external system integration"
    )
    code: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    name_ar: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("department.id"), nullable=True
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="employees")
    meal_request_lines: Mapped[List["MealRequestLine"]] = relationship(
        back_populates="employee"
    )
    security_user: Mapped[Optional["SecurityUser"]] = relationship(
        back_populates="employee"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="employee",
        foreign_keys="[User.employee_id]",
        uselist=False,  # One-to-one relationship (User.employee_id is unique)
        lazy="raise_on_sql",  # Prevent accidental lazy loading in async context
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        """Get name for the specified locale (ar/en). Defaults to Arabic."""
        if locale and locale.lower() == "en":
            return self.name_en or ""
        return self.name_ar or ""

    def __repr__(self):
        return (
            f"<Employee(id={self.id}, code={self.code}, name_en='{self.name_en}', "
            f"name_ar='{self.name_ar}', title='{self.title}', is_active={self.is_active}, "
            f"department_id={self.department_id})>"
        )


class Department(Base):
    __tablename__ = "department"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_en: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    name_ar: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    # Hierarchical structure
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("department.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    employees: Mapped[List["Employee"]] = relationship(
        back_populates="department"
    )
    department_assignments: Mapped[List["DepartmentAssignment"]] = (
        relationship(back_populates="department")
    )
    # Self-referencing relationship for parent/children
    parent: Mapped[Optional["Department"]] = relationship(
        "Department", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Department"]] = relationship(
        "Department", back_populates="parent"
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        """Get name for the specified locale (ar/en). Defaults to Arabic."""
        if locale and locale.lower() == "en":
            return self.name_en
        return self.name_ar

    def __repr__(self):
        return f"<Department(id={self.id}, name_en='{self.name_en}', name_ar='{self.name_ar}', parent_id={self.parent_id})>"


class DepartmentAssignment(Base):
    __tablename__ = "department_assignment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("department.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    # HRIS sync tracking
    is_synced_from_hris: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    department: Mapped["Department"] = relationship(
        back_populates="department_assignments"
    )
    user: Mapped["User"] = relationship(
        back_populates="department_assignments",
        foreign_keys="DepartmentAssignment.user_id",
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys="DepartmentAssignment.created_by_id",
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys="DepartmentAssignment.updated_by_id",
    )

    def __repr__(self):
        return (
            f"<DepartmentAssignment(id={self.id}, department_id={self.department_id}, "
            f"user_id={self.user_id}, is_synced_from_hris={self.is_synced_from_hris}, "
            f"is_active={self.is_active})>"
        )


# In MealRequest model
class MealRequest(Base):
    __tablename__ = "meal_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requester_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    status_id: Mapped[int] = mapped_column(
        ForeignKey("meal_request_status.id"), nullable=False
    )
    meal_type_id: Mapped[int] = mapped_column(
        ForeignKey("meal_type.id"), nullable=False
    )
    request_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    closed_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    closed_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Self-referencing FK to track copied requests
    # Points to the original request when this is a copy
    original_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("meal_request.id"), nullable=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Existing Relationships
    requester: Mapped["User"] = relationship(
        back_populates="meal_requests_requested", foreign_keys=[requester_id]
    )
    closed_by: Mapped["User"] = relationship(
        back_populates="meal_requests_closed", foreign_keys=[closed_by_id]
    )
    status: Mapped["MealRequestStatus"] = relationship(
        back_populates="meal_requests"
    )
    meal_type: Mapped["MealType"] = relationship(
        back_populates="meal_requests"
    )
    meal_request_lines: Mapped[List["MealRequestLine"]] = relationship(
        back_populates="meal_request"
    )
    # Self-referencing relationship for copied requests
    original_request: Mapped[Optional["MealRequest"]] = relationship(
        "MealRequest",
        remote_side=[id],
        foreign_keys=[original_request_id],
        backref="copies",
    )

    def __repr__(self):
        return (
            f"<MealRequest(id={self.id}, requester_id={self.requester_id}, "
            f"status_id={self.status_id}, meal_type_id={self.meal_type_id}, "
            f"request_time={self.request_time}, closed_by_id={
                self.closed_by_id}, "
            f"closed_time={self.closed_time})>"
        )


# In MealRequestLine model
class MealRequestLine(Base):
    __tablename__ = "meal_request_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id"), nullable=False
    )
    employee_code: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    meal_request_id: Mapped[int] = mapped_column(
        ForeignKey("meal_request.id"), nullable=False
    )
    attendance_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shift_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    employee: Mapped["Employee"] = relationship(
        back_populates="meal_request_lines"
    )
    meal_request: Mapped["MealRequest"] = relationship(
        back_populates="meal_request_lines"
    )

    # New Logging Relationship
    meal_request_line_logs: Mapped[List["LogMealRequestLine"]] = relationship(
        back_populates="meal_request_line"
    )

    # Attendance relationship (1:1 with MealRequestLineAttendance)
    attendance: Mapped[Optional["MealRequestLineAttendance"]] = relationship(
        "MealRequestLineAttendance",
        back_populates="meal_request_line",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<MealRequestLine(id={self.id}, employee_id={self.employee_id}, "
            f"department_id={self.department_id}, meal_request_id={
                self.meal_request_id}, "
            f"shift_hours={self.shift_hours}, is_accepted={self.is_accepted})>"
        )


class MealRequestLineAttendance(Base):
    """
    Attendance data for a MealRequestLine, synced from TMS.

    This is a 1:1 relationship with MealRequestLine. Attendance data is populated
    by a background sync job that queries TMS for attendance records matching
    the employee_code and attendance_date of existing MealRequestLines.
    """

    __tablename__ = "meal_request_line_attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_request_line_id: Mapped[int] = mapped_column(
        ForeignKey("meal_request_line.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1:1 with MealRequestLine
        index=True,
    )
    employee_code: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )

    # Attendance times from TMS (stored in UTC)
    attendance_in: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attendance_out: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Working hours calculated from in/out times
    working_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(4, 2), nullable=True
    )

    # Sync tracking
    attendance_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship back to MealRequestLine
    meal_request_line: Mapped["MealRequestLine"] = relationship(
        "MealRequestLine",
        back_populates="attendance",
    )

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


class MealRequestStatus(Base):
    __tablename__ = "meal_request_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name_ar: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="Arabic name"
    )
    name_en: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="English name"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Whether this status is active",
    )

    # Relationships
    meal_requests: Mapped[List["MealRequest"]] = relationship(
        back_populates="status"
    )

    def __repr__(self):
        return f"<MealRequestStatus(id={self.id}, name_ar='{self.name_ar}', name_en='{self.name_en}', is_active={self.is_active})>"


class MealType(Base):
    __tablename__ = "meal_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    name_ar: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )

    # Priority field - higher value = higher priority (default selection)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, index=True
    )

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    # Relationships
    meal_requests: Mapped[List["MealRequest"]] = relationship(
        back_populates="meal_type"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        foreign_keys=[created_by_id], back_populates="meal_types_created"
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        foreign_keys=[updated_by_id], back_populates="meal_types_updated"
    )

    def __repr__(self):
        return f"<MealType(id={self.id}, name_en='{self.name_en}', name_ar='{self.name_ar}', is_active={self.is_active})>"

    def get_name(self, locale: Optional[str] = None) -> str:
        """Get localized name based on locale."""
        if locale and locale.lower() == "en":
            return self.name_en or ""
        return self.name_ar or ""


class Email(Base):
    __tablename__ = "email"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    address: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("email_role.id"), nullable=False
    )

    # Relationships
    role: Mapped["EmailRole"] = relationship(back_populates="emails")

    def __repr__(self):
        return f"<Email(id={self.id}, address='{
            self.address}', role_id={self.role_id})>"


class EmailRole(Base):
    __tablename__ = "email_role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    emails: Mapped[List["Email"]] = relationship(back_populates="role")

    def __repr__(self):
        return f"<EmailRole(id={self.id}, name='{self.name}')>"


class RolePermission(Base):
    __tablename__ = "role_permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    user: Mapped["User"] = relationship(back_populates="role_permissions")

    def __repr__(self):
        return (
            f"<RolePermission(id={self.id}, role_id={self.role_id}, "
            f"user_id={self.user_id})>"
        )


class LogPermission(Base):
    __tablename__ = "log_permission"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id"), nullable=False
    )
    admin_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    effected_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="permission_logs_effected",
    )
    admin: Mapped["User"] = relationship(
        "User",
        foreign_keys=[admin_id],
        back_populates="permission_logs_admin",
    )
    role: Mapped["Role"] = relationship(back_populates="permission_logs_admin")

    def __repr__(self):
        return (
            f"<LogPermission(id={self.id}, user_id={
                self.user_id}, "
            f"admin_id={self.admin_id}, action='{
                self.action}', timestamp={self.timestamp})>"
        )


class LogMealRequestLine(Base):
    __tablename__ = "log_meal_request_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_request_line_id: Mapped[int] = mapped_column(
        ForeignKey("meal_request_line.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    is_successful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    meal_request_line: Mapped["MealRequestLine"] = relationship(
        "MealRequestLine", back_populates="meal_request_line_logs"
    )
    user: Mapped["User"] = relationship(
        "User", back_populates="meal_request_line_logs"
    )

    def __repr__(self):
        return (
            f"<LogMealRequestLine(id={self.id}, meal_request_line_id={self.meal_request_line_id}, "
            f"user_id={self.user_id}, action='{self.action}', "
            f"timestamp={self.timestamp})>"
        )


class LogAuthentication(Base):
    """
    Authentication Audit Log - Tracks all authentication events.

    Logs: login success/failure, logout, token refresh, session revocation
    """

    __tablename__ = "log_authentication"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_successful: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default="1"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_fingerprint: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Relationship
    user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[user_id], backref="auth_logs"
    )

    def __repr__(self):
        return (
            f"<LogAuthentication(id={self.id}, action='{self.action}', "
            f"user_id={self.user_id}, is_successful={self.is_successful}, "
            f"timestamp={self.timestamp})>"
        )


class LogMealRequest(Base):
    """
    Meal Request Audit Log - Tracks meal request lifecycle events.

    Logs: create, update_status, delete, copy, approve, reject
    """

    __tablename__ = "log_meal_request"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meal_request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("meal_request.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_successful: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default="1"
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    new_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Relationships
    user: Mapped["User"] = relationship(
        foreign_keys=[user_id], backref="meal_request_logs"
    )
    meal_request: Mapped[Optional["MealRequest"]] = relationship(
        foreign_keys=[meal_request_id], backref="audit_logs"
    )

    def __repr__(self):
        return (
            f"<LogMealRequest(id={self.id}, action='{self.action}', "
            f"meal_request_id={self.meal_request_id}, user_id={self.user_id}, "
            f"timestamp={self.timestamp})>"
        )


class LogUser(Base):
    """
    User Management Audit Log - Tracks user CRUD operations.

    Logs: create, update_profile, update_status, delete, password_change, role_assignment
    """

    __tablename__ = "log_user"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    admin_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_successful: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default="1"
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    new_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Relationships
    admin: Mapped["User"] = relationship(
        foreign_keys=[admin_id], backref="user_logs_as_admin"
    )
    target_user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[target_user_id], backref="user_logs_as_target"
    )

    def __repr__(self):
        return (
            f"<LogUser(id={self.id}, action='{self.action}', "
            f"admin_id={self.admin_id}, target_user_id={self.target_user_id}, "
            f"timestamp={self.timestamp})>"
        )


class LogRole(Base):
    """
    Role Management Audit Log - Tracks role and permission changes.

    Logs: create_role, update_role, delete_role, assign_page, revoke_page, update_status
    """

    __tablename__ = "log_role"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    admin_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("role.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_successful: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default="1"
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    new_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Relationships
    admin: Mapped["User"] = relationship(
        foreign_keys=[admin_id], backref="role_logs"
    )
    role: Mapped[Optional["Role"]] = relationship(
        foreign_keys=[role_id], backref="audit_logs"
    )

    def __repr__(self):
        return (
            f"<LogRole(id={self.id}, action='{self.action}', "
            f"admin_id={self.admin_id}, role_id={self.role_id}, "
            f"timestamp={self.timestamp})>"
        )


class LogConfiguration(Base):
    """
    Configuration Audit Log - Tracks system configuration changes.

    Entity types: meal_type, department, page, department_assignment
    Actions: create, update, delete
    """

    __tablename__ = "log_configuration"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    admin_id: Mapped[str] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_successful: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default="1"
    )
    old_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    new_value: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    # Composite index for entity lookup
    __table_args__ = (
        Index("idx_log_config_entity", "entity_type", "entity_id"),
        {"mysql_engine": "InnoDB"},
    )

    # Relationship
    admin: Mapped["User"] = relationship(
        foreign_keys=[admin_id], backref="configuration_logs"
    )

    def __repr__(self):
        return (
            f"<LogConfiguration(id={self.id}, entity_type='{self.entity_type}', "
            f"entity_id={self.entity_id}, action='{self.action}', "
            f"created_at={self.created_at})>"
        )


class LogReplication(Base):
    """
    Replication Audit Log - Tracks data replication events from external systems.

    Operations: hris_department_sync, hris_employee_sync, hris_security_user_sync, attendance_sync
    """

    __tablename__ = "log_replication"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
    admin_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    operation_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    is_successful: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, server_default="1"
    )

    # Summary metrics
    records_processed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_created: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_skipped: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_failed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Details
    source_system: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Composite index for operation lookup
    __table_args__ = (
        Index("idx_log_replication_operation_timestamp", "operation_type", "timestamp"),
        {"mysql_engine": "InnoDB"},
    )

    # Relationship
    admin: Mapped[Optional["User"]] = relationship(
        foreign_keys=[admin_id], backref="replication_logs"
    )

    def __repr__(self):
        return (
            f"<LogReplication(id={self.id}, operation_type='{self.operation_type}', "
            f"is_successful={self.is_successful}, "
            f"timestamp={self.timestamp})>"
        )


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    token_type: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False
    )
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship()

    def __repr__(self):
        return (
            f"<RevokedToken(id={self.id}, jti='{self.jti}', "
            f"token_type='{self.token_type}', user_id={self.user_id})>"
        )


class Session(Base):
    """
    Session model for stateful authentication with refresh tokens.

    Tracks user sessions with device information and revocation capability.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("user.id"), nullable=False, index=True
    )
    refresh_token_id: Mapped[str] = mapped_column(
        CHAR(36), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked: Mapped[bool] = mapped_column(
        TINYINT(1), nullable=False, default=False, server_default="0"
    )
    device_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True
    )
    fingerprint: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    session_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self):
        return (
            f"<Session(id={self.id}, user_id={self.user_id}, "
            f"refresh_token_id={self.refresh_token_id}, revoked={self.revoked})>"
        )


class DomainUser(Base):
    """
    Domain User model for caching Active Directory user information.

    Stores user details fetched from Active Directory for quick access
    without needing to query AD repeatedly.
    """

    __tablename__ = "domain_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    office: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    manager: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self):
        return (
            f"<DomainUser(id={self.id}, username='{self.username}', "
            f"full_name='{self.full_name}')>"
        )


# -------------------
# Scheduler Models
# -------------------


class TaskFunction(Base):
    """
    Predefined task functions that can be scheduled.

    Stores the mapping between a logical task key and its Python function path.
    Users can only schedule jobs using these predefined functions.
    """

    __tablename__ = "task_function"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    # Unique key identifier (e.g., "attendance_sync", "data_cleanup")
    key: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    # Python function path (e.g., "utils.sync_attendance.run_attendance_sync")
    function_path: Mapped[str] = mapped_column(String(256), nullable=False)
    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(128), nullable=False)
    # Bilingual description fields
    description_en: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    description_ar: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    scheduled_jobs: Mapped[list["ScheduledJob"]] = relationship(
        back_populates="task_function"
    )

    def __repr__(self):
        return f"<TaskFunction(id={self.id}, key='{self.key}', name_en='{self.name_en}')>"


class SchedulerExecutionStatus(Base):
    """
    Scheduler execution status lookup table with bilingual support.

    Predefined statuses: pending, running, success, failed
    """

    __tablename__ = "scheduler_execution_status"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    # Status code (e.g., "pending", "running", "success", "failed")
    code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    # Display order
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Relationships
    executions: Mapped[list["ScheduledJobExecution"]] = relationship(
        back_populates="status_ref"
    )

    def __repr__(self):
        return f"<SchedulerExecutionStatus(id={self.id}, code='{self.code}', name_en='{self.name_en}')>"


class SchedulerJobType(Base):
    """
    Scheduler job type lookup table with bilingual support.

    Predefined types: interval, cron
    """

    __tablename__ = "scheduler_job_type"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    # Type code (e.g., "interval", "cron")
    code: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(String(64), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(64), nullable=False)
    # Bilingual description
    description_en: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    description_ar: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )
    # Display order
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    # Relationships
    scheduled_jobs: Mapped[list["ScheduledJob"]] = relationship(
        back_populates="job_type_ref"
    )

    def __repr__(self):
        return f"<SchedulerJobType(id={self.id}, code='{self.code}', name_en='{self.name_en}')>"


class ScheduledJob(Base):
    """
    Scheduled job definition.

    Stores job configuration including schedule type (interval or cron),
    execution settings, and audit information.
    References a predefined TaskFunction and JobType.
    """

    __tablename__ = "scheduled_job"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    # Reference to predefined task function
    task_function_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("task_function.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Reference to job type
    job_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scheduler_job_type.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Schedule-specific name (optional override of task function name)
    name_en: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    name_ar: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Schedule-specific description (optional override)
    description_en: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    description_ar: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    # Interval schedule fields (used when job_type = "interval")
    interval_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    interval_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    interval_hours: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    interval_days: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    # Cron schedule (used when job_type = "cron")
    cron_expression: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    # Execution settings
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_instances: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    misfire_grace_time: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300
    )
    coalesce: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    # Status flags
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time job was triggered",
    )
    # Audit fields
    created_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_id: Mapped[Optional[str]] = mapped_column(
        CHAR(36), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    task_function: Mapped["TaskFunction"] = relationship(
        back_populates="scheduled_jobs"
    )
    job_type_ref: Mapped["SchedulerJobType"] = relationship(
        back_populates="scheduled_jobs"
    )
    executions: Mapped[List["ScheduledJobExecution"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    locks: Mapped[List["ScheduledJobLock"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    created_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[created_by_id]
    )
    updated_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[updated_by_id]
    )

    def get_name(self, locale: Optional[str] = None) -> str:
        """Get name for the specified locale (ar/en). Falls back to task function name."""
        if locale and locale.lower() == "ar":
            return self.name_ar or (
                self.task_function.name_ar if self.task_function else ""
            )
        return self.name_en or (
            self.task_function.name_en if self.task_function else ""
        )

    def get_description(self, locale: Optional[str] = None) -> Optional[str]:
        """Get description for the specified locale (ar/en). Falls back to task function description."""
        if locale and locale.lower() == "ar":
            return self.description_ar or (
                self.task_function.description_ar
                if self.task_function
                else None
            )
        return self.description_en or (
            self.task_function.description_en if self.task_function else None
        )

    @property
    def job_key(self) -> str:
        """Get the job key from the associated task function."""
        return self.task_function.key if self.task_function else ""

    @property
    def job_function(self) -> str:
        """Get the function path from the associated task function."""
        return self.task_function.function_path if self.task_function else ""

    @property
    def job_type(self) -> str:
        """Get the job type code from the associated job type."""
        return self.job_type_ref.code if self.job_type_ref else ""

    def __repr__(self):
        return (
            f"<ScheduledJob(id={self.id}, task_function_id={self.task_function_id}, "
            f"job_type_id={self.job_type_id}, is_enabled={self.is_enabled})>"
        )


class ScheduledJobExecution(Base):
    """
    Job execution history record.

    Tracks every execution with timing, status, and error information.
    Records are automatically cleaned up after 30 days retention.
    """

    __tablename__ = "scheduled_job_execution"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scheduled_job.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )
    run_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Outcome - reference to execution status
    status_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scheduler_execution_status.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )
    # Runtime context
    executor_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    host_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    # Timestamp for cleanup
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    job: Mapped["ScheduledJob"] = relationship(back_populates="executions")
    status_ref: Mapped["SchedulerExecutionStatus"] = relationship(
        back_populates="executions"
    )

    @property
    def status(self) -> str:
        """Get the status code from the associated execution status."""
        return self.status_ref.code if self.status_ref else ""

    def __repr__(self):
        return (
            f"<ScheduledJobExecution(id={self.id}, job_id={self.job_id}, "
            f"status_id={self.status_id}, scheduled_at={self.scheduled_at})>"
        )


class ScheduledJobLock(Base):
    """
    Distributed lock for job execution.

    Prevents duplicate executions across multiple scheduler instances.
    Locks expire after a configurable duration and are cleaned up automatically.
    """

    __tablename__ = "scheduled_job_lock"
    __table_args__ = (
        UniqueConstraint(
            "job_id", "execution_id", name="uq_job_lock_job_execution"
        ),
        {"mysql_engine": "InnoDB"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("scheduled_job.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_id: Mapped[str] = mapped_column(String(36), nullable=False)
    executor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    host_name: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    job: Mapped["ScheduledJob"] = relationship(back_populates="locks")

    def __repr__(self):
        return (
            f"<ScheduledJobLock(id={self.id}, job_id={self.job_id}, "
            f"executor_id='{self.executor_id}', expires_at={self.expires_at})>"
        )


class SchedulerInstance(Base):
    """
    Scheduler instance registry for coordination.

    Tracks active scheduler instances for heartbeat monitoring
    and distributed coordination between embedded and standalone modes.
    """

    __tablename__ = "scheduler_instance"

    id: Mapped[str] = mapped_column(
        CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    instance_name: Mapped[str] = mapped_column(String(128), nullable=False)
    host_name: Mapped[str] = mapped_column(String(128), nullable=False)
    process_id: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # "embedded" or "standalone"
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="starting", index=True
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self):
        return (
            f"<SchedulerInstance(id={self.id}, instance_name='{self.instance_name}', "
            f"mode='{self.mode}', status='{self.status}')>"
        )
