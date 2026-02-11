"""HRIS Repository - Data access for employee data from HRIS system."""

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional

from core.exceptions import DatabaseError
from db.schemas import (
    AttendanceRecord,
    Department,
    DepartmentAssignmentRecord,
    Employee,
    EmployeeShift,
    SecurityUser as SecurityUserModel,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)


class HRISRepository:
    """Repository for HRIS employee and organizational data."""

    def __init__(self, session: AsyncSession):
        """Initialize HRIS repository with session."""
        self.session = session

    async def get_active_employees(
        self,
    ) -> Optional[List[Employee]]:
        """
        Get all active employees from HRIS.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of active employees, or None if no employees found
        """
        try:
            stmt = text(
                """
                SELECT
                    Emp.[ID] AS id,
                    Emp.[Code] AS code,
                    CONCAT(
                        Emp.[ArFName], ' ',
                        Emp.[ArSName], ' ',
                        Emp.[ArThName], ' ',
                        Emp.[ArLName]
                    ) AS name_ar,
                    CONCAT(
                        Emp.[EnFName], ' ',
                        Emp.[EnSName], ' ',
                        Emp.[EnThName], ' ',
                        Emp.[EnLName]
                    ) AS name_en,
                    T.[EnName] AS title,
                    P.IsActive AS is_active,
                    OU.[ID] AS department_id
                FROM
                    [HMIS-AMH].[dbo].[HR_Employee] AS Emp
                    JOIN [HMIS-AMH].[dbo].[HR_EmployeePosition] AS P ON P.EmployeeID = Emp.ID
                    JOIN [HMIS-AMH].[dbo].[HR_Position] AS T ON P.PositionID = T.ID
                    JOIN [HMIS-AMH].[dbo].[HR_OrganizationUnit] AS OU ON P.OrgUnitID = OU.ID
                WHERE
                    P.IsActive = 1
            """
            )

            try:
                result = await session.execute(stmt)
                rows = result.fetchall()
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning(
                        "HRIS database connection closed, returning empty list"
                    )
                    return None
                raise

            if not rows:
                return None

            employees = []
            for row in rows:
                employee = Employee(
                    id=row[0],
                    code=row[1],
                    name_ar=row[2],
                    name_en=row[3],
                    title=row[4],
                    is_active=bool(row[5]),
                    department_id=row[6],
                )
                employees.append(employee)

            return employees

        except Exception as e:
            raise DatabaseError(f"Failed to get active employees: {str(e)}")

    async def get_employee_by_code(
        self,
        session: AsyncSession,
        emp_code: int,
    ) -> Optional[Employee]:
        """
        Get a single employee by code from HRIS.

        Args:
            session: HRIS AsyncSession
            emp_code: Employee code

        Returns:
            Employee record, or None if not found
        """
        try:
            stmt = text(
                """
                SELECT TOP 1
                    Emp.[ID] AS id,
                    Emp.[Code] AS code,
                    CONCAT(
                        Emp.[ArFName], ' ',
                        Emp.[ArSName], ' ',
                        Emp.[ArThName], ' ',
                        Emp.[ArLName]
                    ) AS name_ar,
                    CONCAT(
                        Emp.[EnFName], ' ',
                        Emp.[EnSName], ' ',
                        Emp.[EnThName], ' ',
                        Emp.[EnLName]
                    ) AS name_en,
                    T.[EnName] AS title,
                    P.IsActive AS is_active,
                    OU.[ID] AS department_id
                FROM
                    [HMIS-AMH].[dbo].[HR_Employee] AS Emp
                    JOIN [HMIS-AMH].[dbo].[HR_EmployeePosition] AS P ON P.EmployeeID = Emp.ID
                    JOIN [HMIS-AMH].[dbo].[HR_Position] AS T ON P.PositionID = T.ID
                    JOIN [HMIS-AMH].[dbo].[HR_OrganizationUnit] AS OU ON P.OrgUnitID = OU.ID
                WHERE
                    Emp.[Code] = :emp_code
            """
            )

            result = await session.execute(stmt, {"emp_code": emp_code})
            row = result.fetchone()

            if not row:
                return None

            return Employee(
                id=row[0],
                code=row[1],
                name_ar=row[2],
                name_en=row[3],
                title=row[4],
                is_active=bool(row[5]),
                department_id=row[6],
            )

        except Exception as e:
            raise DatabaseError(f"Failed to get employee by code: {str(e)}")

    async def get_departments(
        self,
        session: AsyncSession,
    ) -> Optional[List[Department]]:
        """
        Get all departments from HRIS.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of departments, or None if no departments found
        """
        try:
            stmt = text(
                """
                SELECT
                    [ID] AS id,
                    [ParentID] AS parent_id,
                    [ArName] AS name_ar,
                    [EnName] AS name_en
                FROM
                    [HMIS-AMH].[dbo].[HR_OrganizationUnit]
                WHERE
                    IsActive = 1
            """
            )

            try:
                result = await session.execute(stmt)
                rows = result.fetchall()
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning(
                        "HRIS database connection closed, returning empty list"
                    )
                    return None
                raise

            if not rows:
                return None

            departments = []
            for row in rows:
                department = Department(
                    id=row[0],
                    parent_id=row[1],
                    name_ar=row[2],
                    name_en=row[3],
                )
                departments.append(department)

            return departments

        except Exception as e:
            raise DatabaseError(f"Failed to get departments: {str(e)}")

    async def get_employees_by_department(
        self,
        session: AsyncSession,
        department_id: int,
    ) -> Optional[List[Employee]]:
        """
        Get all active employees in a specific department.

        Args:
            session: HRIS AsyncSession
            department_id: Department ID

        Returns:
            List of employees in the department, or None if none found
        """
        try:
            stmt = text(
                """
                SELECT
                    Emp.[ID] AS id,
                    Emp.[Code] AS code,
                    CONCAT(
                        Emp.[ArFName], ' ',
                        Emp.[ArSName], ' ',
                        Emp.[ArThName], ' ',
                        Emp.[ArLName]
                    ) AS name_ar,
                    CONCAT(
                        Emp.[EnFName], ' ',
                        Emp.[EnSName], ' ',
                        Emp.[EnThName], ' ',
                        Emp.[EnLName]
                    ) AS name_en,
                    T.[EnName] AS title,
                    P.IsActive AS is_active,
                    OU.[ID] AS department_id
                FROM
                    [HMIS-AMH].[dbo].[HR_Employee] AS Emp
                    JOIN [HMIS-AMH].[dbo].[HR_EmployeePosition] AS P ON P.EmployeeID = Emp.ID
                    JOIN [HMIS-AMH].[dbo].[HR_Position] AS T ON P.PositionID = T.ID
                    JOIN [HMIS-AMH].[dbo].[HR_OrganizationUnit] AS OU ON P.OrgUnitID = OU.ID
                WHERE
                    P.IsActive = 1
                    AND OU.[ID] = :department_id
            """
            )

            result = await session.execute(stmt, {"department_id": department_id})
            rows = result.fetchall()

            if not rows:
                return None

            employees = []
            for row in rows:
                employee = Employee(
                    id=row[0],
                    code=row[1],
                    name_ar=row[2],
                    name_en=row[3],
                    title=row[4],
                    is_active=bool(row[5]),
                    department_id=row[6],
                )
                employees.append(employee)

            return employees

        except Exception as e:
            raise DatabaseError(f"Failed to get employees by department: {str(e)}")

    async def get_employees_grouped_by_department(
        self,
        session: AsyncSession,
    ) -> Optional[Dict[int, List[Employee]]]:
        """
        Get all active employees grouped by department.

        Args:
            session: HRIS AsyncSession

        Returns:
            Dictionary mapping department ID to list of employees
        """
        try:
            employees = await self.get_active_employees(session)

            if not employees:
                return None

            grouped = defaultdict(list)
            for employee in employees:
                grouped[employee.department_id].append(employee)

            return dict(grouped)

        except Exception as e:
            raise DatabaseError(f"Failed to group employees by department: {str(e)}")

    async def get_employee_by_id(
        self,
        session: AsyncSession,
        emp_id: int,
    ) -> Optional[Employee]:
        """
        Get a single employee by ID from HRIS.

        Args:
            session: HRIS AsyncSession
            emp_id: Employee ID

        Returns:
            Employee record, or None if not found
        """
        try:
            stmt = text(
                """
                SELECT TOP 1
                    Emp.[ID] AS id,
                    Emp.[Code] AS code,
                    CONCAT(
                        Emp.[ArFName], ' ',
                        Emp.[ArSName], ' ',
                        Emp.[ArThName], ' ',
                        Emp.[ArLName]
                    ) AS name_ar,
                    CONCAT(
                        Emp.[EnFName], ' ',
                        Emp.[EnSName], ' ',
                        Emp.[EnThName], ' ',
                        Emp.[EnLName]
                    ) AS name_en,
                    T.[EnName] AS title,
                    P.IsActive AS is_active,
                    OU.[ID] AS department_id
                FROM
                    [HMIS-AMH].[dbo].[HR_Employee] AS Emp
                    JOIN [HMIS-AMH].[dbo].[HR_EmployeePosition] AS P ON P.EmployeeID = Emp.ID
                    JOIN [HMIS-AMH].[dbo].[HR_Position] AS T ON P.PositionID = T.ID
                    JOIN [HMIS-AMH].[dbo].[HR_OrganizationUnit] AS OU ON P.OrgUnitID = OU.ID
                WHERE
                    Emp.[ID] = :emp_id
            """
            )

            result = await session.execute(stmt, {"emp_id": emp_id})
            row = result.fetchone()

            if not row:
                return None

            return Employee(
                id=row[0],
                code=row[1],
                name_ar=row[2],
                name_en=row[3],
                title=row[4],
                is_active=bool(row[5]),
                department_id=row[6],
            )

        except Exception as e:
            raise DatabaseError(f"Failed to get employee by ID: {str(e)}")

    # === Replication Methods ===

    async def get_security_users(
        self, session: AsyncSession
    ) -> Optional[List[SecurityUserModel]]:
        """
        Get security users from HRIS for replication.

        Returns all active, non-locked users from HRIS (no role filtering).

        Args:
            session: HRIS AsyncSession

        Returns:
            List of SecurityUser model instances
        """
        try:
            # Query to get ALL active, non-locked users (no role filter)
            # Username validation: Only import users with dots (.) or dashes (-) to exclude test accounts
            stmt = text(
                """
                SELECT
                    S.ID AS id,
                    S.Name AS username,
                    S.isDeleted AS is_deleted,
                    S.isLocked AS is_locked,
                    S.EmpId AS emp_id
                FROM
                    [HMIS-AMH].[Security].[User] S
                WHERE
                    S.isDeleted <> 1
                    AND S.isLocked <> 1
                    AND (S.Name LIKE '%.%' OR S.Name LIKE '%-%')
            """
            )

            logger.info("Fetching all active SecurityUsers from HRIS (including EmpId)")

            try:
                result = await session.execute(stmt)
                rows = result.fetchall()
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning(
                        "HRIS database connection closed, returning empty list"
                    )
                    return None
                raise

            if not rows:
                logger.warning("No SecurityUsers found in HRIS")
                return None

            logger.info(f"Retrieved {len(rows)} SecurityUsers from HRIS")

            security_users = []
            for row in rows:
                # Create SecurityUser model instance
                security_user = SecurityUserModel(
                    id=row[0],
                    user_name=row[1],
                    is_deleted=bool(row[2]),
                    is_locked=bool(row[3]),
                    emp_id=row[4] if len(row) > 4 and row[4] is not None else None,
                )
                security_users.append(security_user)

            logger.info(
                f"Successfully created {len(security_users)} SecurityUser model instances"
            )
            return security_users

        except Exception as e:
            raise DatabaseError(f"Failed to get security users: {str(e)}")

    async def get_department_assignments(
        self,
        session: AsyncSession,
    ) -> Optional[List["DepartmentAssignmentRecord"]]:
        """
        Get department assignments from HRIS TMS_ForwardEdit table.

        Maps: EmployeeID -> employee_id, OrgUnitID -> department_id

        Args:
            session: HRIS AsyncSession

        Returns:
            List of DepartmentAssignmentRecord with employee_id and department_id
        """
        try:
            logger.info(
                "Fetching department assignments from HRIS TMS_ForwardEdit table"
            )

            stmt = text(
                """
                SELECT
                    [EmployeeID] AS employee_id,
                    [OrgUnitID] AS department_id
                FROM
                    [HMIS-AMH].dbo.TMS_ForwardEdit
                ORDER BY
                    [EmployeeID], [OrgUnitID]
            """
            )

            try:
                result = await session.execute(stmt)
                rows = result.fetchall()
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning(
                        "HRIS database connection closed, returning empty list"
                    )
                    return None
                raise

            if not rows:
                logger.warning("No department assignments found in TMS_ForwardEdit")
                return None

            logger.info(
                f"Retrieved {len(rows)} department assignments from TMS_ForwardEdit"
            )

            assignments = []
            for row in rows:
                assignment = DepartmentAssignmentRecord(
                    employee_id=row[0],
                    department_id=row[1],
                )
                assignments.append(assignment)

            # Log sample of first 5 assignments
            logger.info("Sample of first 5 department assignments:")
            for idx, assign in enumerate(assignments[:5]):
                logger.info(
                    f"  {idx + 1}. EmployeeID={assign.employee_id}, DepartmentID={assign.department_id}"
                )

            logger.info(
                f"Successfully created {len(assignments)} DepartmentAssignmentRecord instances"
            )
            return assignments

        except Exception as e:
            raise DatabaseError(f"Failed to get department assignments: {str(e)}")

    async def deactivate_all_employees(self) -> None:
        """
        Deactivate all employees in the local database.

        Args:
            session: Local database AsyncSession
        """
        try:
            stmt = text(
                """
                UPDATE employee
                SET is_active = 0
                WHERE is_active = 1
            """
            )
            await session.execute(stmt)
        except Exception as e:
            raise DatabaseError(f"Failed to deactivate all employees: {str(e)}")

    async def deactivate_all_security_users(self, session: AsyncSession) -> None:
        """
        Deactivate all security users in the local database by marking them as deleted.

        Args:
            session: Local database AsyncSession
        """
        try:
            stmt = text(
                """
                UPDATE security_user
                SET is_deleted = 1
                WHERE is_deleted = 0
            """
            )
            await session.execute(stmt)
        except Exception as e:
            raise DatabaseError(f"Failed to deactivate all security users: {str(e)}")

    async def delete_all_department_assignments(self, session: AsyncSession) -> None:
        """
        Delete all department assignments in the local database.

        Args:
            session: Local database AsyncSession
        """
        try:
            stmt = text(
                """
                DELETE FROM department_assignment
            """
            )
            await session.execute(stmt)
        except Exception as e:
            raise DatabaseError(
                f"Failed to delete all department assignments: {str(e)}"
            )

    async def deactivate_hris_department_assignments(
        self, session: AsyncSession
    ) -> int:
        """
        Deactivate existing HRIS-synced department assignments only.

        Only deactivates records where is_synced_from_hris=True.
        Preserves manual assignments (is_synced_from_hris=False).

        Args:
            session: Local database AsyncSession

        Returns:
            Number of records deactivated
        """
        try:
            stmt = text(
                """
                UPDATE department_assignment
                SET is_active = 0, updated_at = NOW()
                WHERE is_synced_from_hris = 1 AND is_active = 1
            """
            )
            result = await session.execute(stmt)
            return result.rowcount or 0
        except Exception as e:
            raise DatabaseError(
                f"Failed to deactivate HRIS department assignments: {str(e)}"
            )

    # === Attendance Methods (TMS) ===

    async def get_attendance_for_employees(
        self,
        session: AsyncSession,
        employee_ids: List[int],
        target_date: date,
    ) -> List[AttendanceRecord]:
        """
        Batch query TMS for attendance by employee IDs and date.

        Args:
            session: HRIS AsyncSession (TMS database)
            employee_ids: List of employee IDs to query
            target_date: Date to fetch attendance for

        Returns:
            List of AttendanceRecord with employee_code, time_in, time_out, working_hours
        """
        if not employee_ids:
            return []

        try:
            # Build parameterized IN clause for employee IDs
            # SQL Server requires a different approach for large IN clauses
            placeholders = ", ".join([f":id_{i}" for i in range(len(employee_ids))])
            params = {f"id_{i}": emp_id for i, emp_id in enumerate(employee_ids)}
            params["target_date"] = target_date

            stmt = text(
                f"""
                SELECT
                    A.[EmployeeId] AS employee_id,
                    A.[InDate] AS time_in,
                    A.[OutDate] AS time_out,
                    DATEDIFF(MINUTE, A.[InDate], A.[OutDate]) / 60.0 AS working_hours
                FROM
                    [HMIS-AMH].dbo.TMS_AttendancePairing  AS A
                WHERE
                    A.[EmployeeId] IN ({placeholders})
                    AND CAST(A.[InDate] AS DATE) = :target_date
            """
            )

            result = await session.execute(stmt, params)
            rows = result.fetchall()

            logger.debug(
                f"TMS query returned {len(rows)} records for {len(employee_ids)} employees on {target_date}"
            )

            attendance_records = []
            for row in rows:
                record = AttendanceRecord(
                    employee_id=row[0],
                    time_in=row[1],
                    time_out=row[2],
                    working_hours=(float(row[3]) if row[3] is not None else None),
                )
                attendance_records.append(record)

            return attendance_records

        except Exception as e:
            raise DatabaseError(f"Failed to get attendance for employees: {str(e)}")

    async def get_attendance_for_employee(
        self,
        session: AsyncSession,
        employee_id: int,
        target_date: date,
    ) -> Optional[AttendanceRecord]:
        """
        Get attendance for a single employee on a specific date.

        Args:
            session: HRIS AsyncSession (TMS database)
            employee_id: Employee ID to query
            target_date: Date to fetch attendance for

        Returns:
            AttendanceRecord if found, None otherwise
        """
        try:
            stmt = text(
                """
                SELECT TOP 1
                    A.[EmployeeId] AS employee_id,
                    A.[InDate] AS time_in,
                    A.[OutDate] AS time_out,
                    DATEDIFF(MINUTE, A.[InDate], A.[OutDate]) / 60.0 AS working_hours
                FROM
                    [HMIS-AMH].dbo.TMS_AttendancePairing  AS A
                WHERE
                    A.[EmployeeId] = :employee_id
                    AND CAST(A.[InDate] AS DATE) = :target_date
            """
            )

            result = await session.execute(
                stmt,
                {
                    "employee_id": employee_id,
                    "target_date": target_date,
                },
            )
            row = result.fetchone()

            if not row:
                return None

            return AttendanceRecord(
                employee_id=row[0],
                time_in=row[1],
                time_out=row[2],
                working_hours=float(row[3]) if row[3] is not None else None,
            )

        except Exception as e:
            raise DatabaseError(f"Failed to get attendance for employee: {str(e)}")

    async def get_today_sign_in_time(
        self,
        session: AsyncSession,
        employee_id: int,
        target_date: date,
    ) -> Optional[datetime]:
        """
        Get today's sign-in time from TMS_Attendance for real-time attendance checking.

        This method queries the TMS_Attendance table (actual attendance records from
        time tracking system) to get the sign-in time for meal request acceptance/rejection.
        This is different from TMS_AttendancePairing which is used for HR-verified auditing.

        Args:
            session: HRIS AsyncSession (TMS database)
            employee_id: Employee ID (HRIS ID) to query
            target_date: Date to fetch attendance for (typically today)

        Returns:
            Sign-in datetime if found, None otherwise
        """
        try:
            stmt = text(
                """
                SELECT TOP 1
                    A.[SignDatetime] AS sign_in_time
                FROM
                    [HMIS-AMH].dbo.TMS_Attendance AS A
                WHERE
                    A.[EmployeeID] = :employee_id
                    AND CAST(A.[SignDatetime] AS DATE) = :target_date
                    AND A.[SignTypeID] = 1
                ORDER BY
                    A.[SignDatetime] ASC
            """
            )

            result = await session.execute(
                stmt,
                {
                    "employee_id": employee_id,
                    "target_date": target_date,
                },
            )
            row = result.fetchone()

            if not row:
                logger.debug(
                    f"No sign-in attendance found for employee {employee_id} on {target_date}"
                )
                return None

            sign_in_time = row[0]
            logger.debug(
                f"Found sign-in time for employee {employee_id}: {sign_in_time}"
            )
            return sign_in_time

        except Exception as e:
            logger.error(
                f"Failed to get sign-in time for employee {employee_id}: {str(e)}"
            )
            raise DatabaseError(f"Failed to get sign-in time for employee: {str(e)}")

    # === Shift Methods (TMS) ===

    async def get_employee_shifts(
        self,
        session: AsyncSession,
        employee_id: int,
        start_date: date,
        end_date: date,
    ) -> List[EmployeeShift]:
        """
        Get shift assignments for an employee within a date range.

        Args:
            session: HRIS AsyncSession (TMS database)
            employee_id: Employee ID in HRIS
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of EmployeeShift records
        """
        try:
            stmt = text(
                """
                SELECT
                    TMS_ShiftAssignment.ID AS id,
                    TMS_ShiftAssignment.EmployeeID AS employee_id,
                    TMS_ShiftAssignment.DurationHours AS duration_hours,
                    TMS_ShiftAssignment.DateFrom AS date_from,
                    ISNULL(TMS_Shift.Code, 'None') AS shift_type
                FROM
                    TMS_ShiftAssignment
                    LEFT JOIN TMS_Shift ON TMS_ShiftAssignment.ShiftID = TMS_Shift.ID
                WHERE
                    TMS_ShiftAssignment.EmployeeID = :employee_id
                    AND CAST(TMS_ShiftAssignment.DateFrom AS DATE) >= :start_date
                    AND CAST(TMS_ShiftAssignment.DateFrom AS DATE) <= :end_date
                ORDER BY
                    TMS_ShiftAssignment.DateFrom DESC
            """
            )

            result = await session.execute(
                stmt,
                {
                    "employee_id": employee_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            rows = result.fetchall()

            shifts = []
            for row in rows:
                shift = EmployeeShift(
                    id=row[0],
                    employee_id=row[1],
                    duration_hours=row[2] or 0,
                    date_from=row[3],
                    shift_type=row[4] or "None",
                )
                shifts.append(shift)

            return shifts

        except Exception as e:
            raise DatabaseError(f"Failed to get employee shifts: {str(e)}")

    async def get_attendance_by_date_range(
        self,
        session: AsyncSession,
        employee_id: int,
        start_date: date,
        end_date: date,
    ) -> List[AttendanceRecord]:
        """
        Get attendance records for an employee within a date range.

        Args:
            session: HRIS AsyncSession (TMS database)
            employee_id: Employee ID to query
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of AttendanceRecord with employee_code, time_in, time_out, working_hours
        """
        try:
            stmt = text(
                """
                SELECT
                    A.[EmployeeId] AS employee_id,
                    A.[InDate] AS time_in,
                    A.[OutDate] AS time_out,
                    DATEDIFF(MINUTE, A.[InDate], A.[OutDate]) / 60.0 AS working_hours
                FROM
                    [HMIS-AMH].dbo.TMS_AttendancePairing  AS A
                WHERE
                    A.[EmployeeId] = :employee_id
                    AND CAST(A.[InDate] AS DATE) >= :start_date
                    AND CAST(A.[InDate] AS DATE) <= :end_date
                ORDER BY
                    A.[InDate] DESC
            """
            )

            result = await session.execute(
                stmt,
                {
                    "employee_id": employee_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            rows = result.fetchall()

            attendance_records = []
            for row in rows:
                record = AttendanceRecord(
                    employee_id=row[0],
                    time_in=row[1],
                    time_out=row[2],
                    working_hours=(float(row[3]) if row[3] is not None else None),
                )
                attendance_records.append(record)

            return attendance_records

        except Exception as e:
            raise DatabaseError(f"Failed to get attendance by date range: {str(e)}")
