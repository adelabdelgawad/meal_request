"""HRIS Service - Business logic for employee data from HRIS system."""

from datetime import date
from typing import List, Optional, Dict

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.hris_repository import HRISRepository
from core.exceptions import ValidationError
from db.schemas import (
    Employee,
    Department,
    AttendanceRecord,
    EmployeeShift,
    DepartmentAssignmentRecord,
)
from core.config import settings


class HRISService:
    """Service for HRIS employee and organizational operations."""

    def __init__(self):
        """Initialize HRIS service."""
        self._repo = HRISRepository(self.session)

    async def get_active_employees(
        self,
        session: AsyncSession,
    ) -> Optional[List[Employee]]:
        """
        Get all active employees from HRIS.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of active employees, or None if none found
        """
        return await self._repo.get_active_employees(session)

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

        Raises:
            ValidationError: If employee code is invalid
        """
        if emp_code <= 0:
            raise ValidationError("Employee code must be positive")

        return await self._repo.get_employee_by_code(session, emp_code)

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

        Raises:
            ValidationError: If employee ID is invalid
        """
        if emp_id <= 0:
            raise ValidationError("Employee ID must be positive")

        return await self._repo.get_employee_by_id(session, emp_id)

    async def get_departments(
        self,
        session: AsyncSession,
    ) -> Optional[List[Department]]:
        """
        Get all departments from HRIS.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of departments, or None if none found
        """
        return await self._repo.get_departments(session)

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

        Raises:
            ValidationError: If department ID is invalid
        """
        if department_id <= 0:
            raise ValidationError("Department ID must be positive")

        return await self._repo.get_employees_by_department(session, department_id)

    async def get_employees_grouped_by_department(
        self,
        session: AsyncSession,
    ) -> Optional[Dict[int, List[Employee]]]:
        """
        Get all active employees grouped by department.

        Args:
            session: HRIS AsyncSession

        Returns:
            Dictionary mapping department ID to list of employees, or None if none found
        """
        return await self._repo.get_employees_grouped_by_department(session)

    async def get_employee_info(
        self,
        session: AsyncSession,
        emp_code: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Optional[Dict]:
        """
        Get complete employee information by code including department and shifts.

        Args:
            session: HRIS AsyncSession
            emp_code: Employee code
            start_date: Optional start date for shifts (defaults to today)
            end_date: Optional end date for shifts (defaults to today)

        Returns:
            Dictionary with employee info, department info, and shifts, or None if not found

        Raises:
            ValidationError: If employee code is invalid
        """
        from datetime import date as date_type

        if emp_code <= 0:
            raise ValidationError("Employee code must be positive")

        employee = await self._repo.get_employee_by_code(session, emp_code)
        if not employee:
            return None

        # Default to today if no dates provided
        if start_date is None:
            start_date = date_type.today()
        if end_date is None:
            end_date = date_type.today()

        shifts = await self._repo.get_employee_shifts(
            session, employee.id, start_date, end_date
        )

        return {
            "employee": employee,
            "shifts": shifts or [],
        }

    async def get_department_summary(
        self,
        session: AsyncSession,
        department_id: int,
    ) -> Optional[Dict]:
        """
        Get department information with employee count.

        Args:
            session: HRIS AsyncSession
            department_id: Department ID

        Returns:
            Dictionary with department info and employee count, or None if not found

        Raises:
            ValidationError: If department ID is invalid
        """
        if department_id <= 0:
            raise ValidationError("Department ID must be positive")

        employees = await self._repo.get_employees_by_department(session, department_id)

        if not employees:
            return None

        # Get first employee to extract department info
        employee = employees[0]

        return {
            "department_id": employee.department_id,
            "employee_count": len(employees),
            "employees": employees,
        }

    # === Replication Methods ===

    async def read_hris_departments(
        self, session: AsyncSession
    ) -> Optional[List[Department]]:
        """
        Read all departments from HRIS for replication.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of departments, or None if none found
        """
        return await self._repo.get_departments(session)

    async def read_hris_active_employees(
        self, session: AsyncSession
    ) -> Optional[List[Employee]]:
        """
        Read all active employees from HRIS for replication.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of active employees, or None if none found
        """
        return await self._repo.get_active_employees(session)

    async def read_hris_security_users(self, session: AsyncSession) -> Optional[List]:
        """
        Read security users from HRIS for replication.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of security users, or None if none found
        """
        return await self._repo.get_security_users(session)

    async def deactivate_all_employees(self, session: AsyncSession) -> None:
        """
        Deactivate all employees in the local database before replication.

        Args:
            session: Local database AsyncSession
        """
        await self._repo.deactivate_all_employees(session)

    async def deactivate_all_security_users(self, session: AsyncSession) -> None:
        """
        Deactivate all security users in the local database before replication.
        Uses SecurityUserRepository for proper ORM-based deactivation.

        Args:
            session: Local database AsyncSession
        """
        from api.repositories.security_user_repository import SecurityUserRepository

        security_user_repo = SecurityUserRepository()
        await security_user_repo.deactivate_all(session)

    async def delete_all_department_assignments(self, session: AsyncSession) -> None:
        """
        Delete all department assignments in the local database before replication.

        Args:
            session: Local database AsyncSession
        """
        await self._repo.delete_all_department_assignments(session)

    async def read_hris_department_assignments(
        self, session: AsyncSession
    ) -> Optional[List[DepartmentAssignmentRecord]]:
        """
        Read department assignments from HRIS TMS_ForwardEdit table for replication.

        Args:
            session: HRIS AsyncSession

        Returns:
            List of department assignments, or None if none found
        """
        return await self._repo.get_department_assignments(session)

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
        return await self._repo.deactivate_hris_department_assignments(session)

    async def sync_security_user_employee_links(
        self,
        session: AsyncSession,
        security_users: Optional[List],
    ) -> int:
        """
        Link local SecurityUser records to local Employee records.

        Matches by: HRIS Security.User.EmpId == HRIS Employee.ID (same person)
        - SecurityUser.emp_id (from HRIS) matches Employee.id (which is HRIS Employee ID)
        - Sets local SecurityUser.employee_id = Employee.id

        Args:
            session: Local database AsyncSession
            security_users: List of SecurityUser Pydantic models from HRIS

        Returns:
            Number of SecurityUsers successfully linked to Employees
        """
        if not security_users:
            return 0

        from api.repositories.employee_repository import EmployeeRepository
        from api.repositories.security_user_repository import SecurityUserRepository

        employee_repo = EmployeeRepository()
        security_repo = SecurityUserRepository()
        linked_count = 0
        not_found_count = 0

        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            f"Processing {len(security_users)} SecurityUsers for Employee linking"
        )
        logger.info("Matching: SecurityUser.emp_id (HRIS) → Employee.id (HRIS ID)")

        no_emp_id_count = 0

        for idx, sec_user in enumerate(security_users):
            try:
                # Skip if SecurityUser has no emp_id from HRIS
                if not sec_user.emp_id:
                    no_emp_id_count += 1
                    if no_emp_id_count <= 3:
                        logger.warning(
                            f"✗ SecurityUser '{sec_user.user_name}' (HRIS ID {sec_user.id}) has no EmpId in HRIS"
                        )
                    continue

                # Find local Employee by HRIS ID (which is now the primary key)
                # SecurityUser.emp_id stores the HRIS Employee.ID
                employee = await employee_repo.get_by_id(session, sec_user.emp_id)

                if employee:
                    # CRITICAL FIX: Look up local SecurityUser by username, not by HRIS ID
                    # The HRIS SecurityUser ID doesn't match the local auto-increment ID
                    local_security_user = await security_repo.get_by_username(
                        session, sec_user.user_name
                    )

                    if local_security_user:
                        # Update local SecurityUser to link to local Employee
                        updated_user = await security_repo.update(
                            session,
                            local_security_user.id,  # Use LOCAL SecurityUser ID, not HRIS ID
                            {"employee_id": employee.id},  # Set to HRIS Employee ID
                        )
                        if updated_user:
                            linked_count += 1
                            if linked_count <= 3:  # Log first 3 successful links
                                logger.info(
                                    f"✓ Linked SecurityUser '{sec_user.user_name}' (local_id={local_security_user.id}, hris_id={sec_user.id}, emp_id={sec_user.emp_id}) "
                                    f"→ Employee {employee.code} (id={employee.id})"
                                )
                    else:
                        not_found_count += 1
                        if not_found_count <= 10:  # Log first 10 failures
                            logger.warning(
                                f"✗ Local SecurityUser not found for username '{sec_user.user_name}' (HRIS ID {sec_user.id})"
                            )
                else:
                    not_found_count += 1
                    if not_found_count <= 10:  # Log first 10 failures
                        logger.warning(
                            f"✗ No Employee found with id={sec_user.emp_id} "
                            f"for SecurityUser '{sec_user.user_name}' (HRIS ID {sec_user.id}, emp_id={sec_user.emp_id})"
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to link SecurityUser '{sec_user.user_name}' (HRIS ID {sec_user.id}): {e}"
                )
                continue

        logger.info(
            f"SecurityUser→Employee linking: {linked_count} linked, {not_found_count} not found, {no_emp_id_count} without EmpId"
        )
        return linked_count

    async def sync_user_employee_links(
        self,
        session: AsyncSession,
    ) -> int:
        """
        Link application users to employees by matching username to SecurityUser.user_name.

        For each User in the database, finds matching SecurityUser by username,
        then links to the same Employee via employee_id.

        Args:
            session: Local database AsyncSession

        Returns:
            Number of users successfully linked to employees
        """
        from sqlalchemy import select, update
        from db.model import User, SecurityUser

        import logging

        logger = logging.getLogger(__name__)

        linked_count = 0

        try:
            # Get all SecurityUsers with employee_id set
            stmt = select(SecurityUser).where(SecurityUser.employee_id.isnot(None))
            result = await session.execute(stmt)
            security_users = result.scalars().all()

            logger.info(
                f"Found {len(security_users)} SecurityUsers with employee_id set"
            )

            if not security_users:
                logger.warning(
                    "No SecurityUsers have employee_id set - cannot link any Users"
                )
                return 0

            # Create mapping of user_name -> employee_id
            username_to_employee = {
                su.user_name: su.employee_id for su in security_users
            }

            logger.info(
                f"Created mapping for {len(username_to_employee)} usernames to employees"
            )
            logger.info(
                f"Sample usernames in mapping: {list(username_to_employee.keys())[:5]}"
            )

            # Get all Users to see how many exist
            user_stmt = select(User)
            user_result = await session.execute(user_stmt)
            all_users = user_result.scalars().all()
            logger.info(f"Total Users in database: {len(all_users)}")
            logger.info(
                f"Sample usernames in User table: {[u.username for u in all_users[:5]]}"
            )

            # Diagnostic: Check username overlap
            user_usernames = {u.username.lower() for u in all_users}
            mapping_usernames = {un.lower() for un in username_to_employee.keys()}
            overlap = user_usernames & mapping_usernames
            logger.info(
                f"Username overlap: {len(overlap)} out of {len(user_usernames)} users match SecurityUser mapping"
            )
            if len(overlap) < len(user_usernames):
                logger.warning(
                    f"Username mismatch detected! Users not in mapping: {sorted(user_usernames - mapping_usernames)[:10]}"
                )
                logger.warning(
                    f"Mapping usernames not in Users: {sorted(mapping_usernames - user_usernames)[:10]}"
                )

            # Update Users with matching usernames (case-insensitive)
            for username, employee_id in username_to_employee.items():
                update_stmt = (
                    update(User)
                    .where(func.lower(User.username) == username.lower())
                    .where(User.employee_id.is_(None))  # Only update if not already set
                    .values(employee_id=employee_id)
                )
                result = await session.execute(update_stmt)
                if result.rowcount > 0:
                    linked_count += result.rowcount
                    if linked_count <= 10:  # Log first 10 successful links
                        logger.info(
                            f"Linked User '{username}' to employee_id {employee_id}"
                        )

            await session.flush()

            logger.info(f"User-employee linking completed: {linked_count} users linked")
            return linked_count

        except Exception as e:
            logger.error(f"Failed to sync user-employee links: {e}", exc_info=True)
            return linked_count

    # === Attendance & Shift Methods (TMS) ===

    def _is_still_on_shift(self, record: AttendanceRecord) -> bool:
        """
        Check if employee is still on shift.

        Returns True if:
          - No out time recorded
          - Out time is less than ATTENDANCE_MIN_SHIFT_HOURS after in time (invalid out)
        Returns False if:
          - Out time is >= ATTENDANCE_MIN_SHIFT_HOURS after in time (valid out, shift completed)
        """
        if not record.time_out:
            return True  # No out = still on shift

        if record.time_in and record.time_out:
            time_diff = record.time_out - record.time_in
            hours_diff = time_diff.total_seconds() / 3600

            if hours_diff < settings.attendance.min_shift_hours:
                return True  # Out too soon = still on shift

        return False  # Valid out = shift completed

    def _filter_on_shift_only(
        self, records: List[AttendanceRecord]
    ) -> List[AttendanceRecord]:
        """
        Filter to only employees currently on shift.

        - Exclude records with valid out (>= ATTENDANCE_MIN_SHIFT_HOURS after in)
        - For invalid outs (< ATTENDANCE_MIN_SHIFT_HOURS), clear time_out and working_hours
        """
        result = []
        for record in records:
            if self._is_still_on_shift(record):
                # Clear invalid out times
                if record.time_out:
                    record.time_out = None
                    record.working_hours = None
                result.append(record)
            # Skip records with valid out (employee left)
        return result

    async def get_employee_shifts(
        self,
        session: AsyncSession,
        employee_id: int,
        start_date: date,
        end_date: date,
    ) -> Optional[List[EmployeeShift]]:
        """
        Get shift assignments for an employee within a date range.

        Args:
            session: HRIS AsyncSession
            employee_id: Employee ID in HRIS
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of EmployeeShift records, or None if none found

        Raises:
            ValidationError: If employee ID is invalid
        """
        if employee_id <= 0:
            raise ValidationError("Employee ID must be positive")

        shifts = await self._repo.get_employee_shifts(
            session, employee_id, start_date, end_date
        )
        return shifts if shifts else None

    async def get_attendance_on_shift(
        self,
        session: AsyncSession,
        employee_code: int,
        start_date: date,
        end_date: date,
    ) -> Optional[List[AttendanceRecord]]:
        """
        Get attendance records for employees currently ON SHIFT.

        Excludes employees who have completed their shift
        (valid out >= ATTENDANCE_MIN_SHIFT_HOURS hours after in).

        Args:
            session: HRIS AsyncSession
            employee_code: Employee code
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of AttendanceRecord for employees still on shift, or None if none found

        Raises:
            ValidationError: If employee code is invalid
        """
        if employee_code <= 0:
            raise ValidationError("Employee code must be positive")

        # Get raw attendance from repository
        records = await self._repo.get_attendance_by_date_range(
            session, employee_code, start_date, end_date
        )

        if not records:
            return None

        # Filter to only on-shift employees
        on_shift_records = self._filter_on_shift_only(records)

        return on_shift_records if on_shift_records else None

    async def get_attendance_raw(
        self,
        session: AsyncSession,
        employee_code: int,
        start_date: date,
        end_date: date,
    ) -> Optional[List[AttendanceRecord]]:
        """
        Get raw attendance records without filtering (for debugging/admin).

        Args:
            session: HRIS AsyncSession
            employee_code: Employee code
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of all AttendanceRecord, or None if none found

        Raises:
            ValidationError: If employee code is invalid
        """
        if employee_code <= 0:
            raise ValidationError("Employee code must be positive")

        return await self._repo.get_attendance_by_date_range(
            session, employee_code, start_date, end_date
        )

    async def sync_user_active_status_from_security_user(
        self, session: AsyncSession
    ) -> Dict[str, int]:
        """
        Sync User.is_active based on SecurityUser.is_deleted/is_locked status.

        Strategy A: Source Tracking with Bypass Logic
        - Only affects HRIS users (user_source='hris')
        - Respects manual overrides (status_override=True)
        - Deactivates users whose SecurityUser is deleted/locked
        - Reactivates users whose SecurityUser is active

        Args:
            session: Local database AsyncSession

        Returns:
            Dict with stats: {"deactivated": int, "reactivated": int, "skipped_manual": int, "skipped_override": int}
        """
        from sqlalchemy import update, select, and_, or_
        from db.model import User, SecurityUser
        import logging

        logger = logging.getLogger(__name__)
        stats = {
            "deactivated": 0,
            "reactivated": 0,
            "skipped_manual": 0,
            "skipped_override": 0,
        }

        try:
            # Count manual users (will be skipped)
            manual_count_stmt = (
                select(func.count())
                .select_from(User)
                .where(User.user_source == "manual")
            )
            manual_result = await session.execute(manual_count_stmt)
            stats["skipped_manual"] = manual_result.scalar() or 0

            # Count override users (will be skipped)
            override_count_stmt = (
                select(func.count())
                .select_from(User)
                .where(and_(User.user_source == "hris", User.status_override == True))
            )
            override_result = await session.execute(override_count_stmt)
            stats["skipped_override"] = override_result.scalar() or 0

            logger.info(
                f"User.is_active sync starting: {stats['skipped_manual']} manual users "
                f"and {stats['skipped_override']} override users will be skipped"
            )

            # Deactivate HRIS users whose SecurityUser is deleted or locked
            # Build subquery to get usernames that should be deactivated
            deactivate_subquery = select(SecurityUser.user_name).where(
                or_(SecurityUser.is_deleted == True, SecurityUser.is_locked == True)
            )

            deactivate_stmt = (
                update(User)
                .where(
                    and_(
                        User.user_source == "hris",  # Only HRIS users
                        User.status_override == False,  # Respect overrides
                        User.username.in_(
                            deactivate_subquery
                        ),  # SecurityUser is deleted/locked
                        User.is_active == True,  # Only update active users
                    )
                )
                .values(is_active=False)
            )

            deactivate_result = await session.execute(deactivate_stmt)
            stats["deactivated"] = deactivate_result.rowcount
            await session.flush()

            logger.info(
                f"Deactivated {stats['deactivated']} HRIS users based on SecurityUser status"
            )

            # Reactivate HRIS users whose SecurityUser is active
            # Build subquery to get usernames that should be reactivated
            reactivate_subquery = select(SecurityUser.user_name).where(
                and_(SecurityUser.is_deleted == False, SecurityUser.is_locked == False)
            )

            reactivate_stmt = (
                update(User)
                .where(
                    and_(
                        User.user_source == "hris",  # Only HRIS users
                        User.status_override == False,  # Respect overrides
                        User.username.in_(
                            reactivate_subquery
                        ),  # SecurityUser is active
                        User.is_active == False,  # Only update inactive users
                    )
                )
                .values(is_active=True)
            )

            reactivate_result = await session.execute(reactivate_stmt)
            stats["reactivated"] = reactivate_result.rowcount
            await session.flush()

            logger.info(
                f"Reactivated {stats['reactivated']} HRIS users based on SecurityUser status"
            )

            logger.info(
                f"User.is_active sync complete: {stats['deactivated']} deactivated, "
                f"{stats['reactivated']} reactivated, "
                f"{stats['skipped_manual']} manual users skipped, "
                f"{stats['skipped_override']} override users skipped"
            )

            return stats

        except Exception as e:
            logger.error(
                f"Failed to sync user active status from SecurityUser: {e}",
                exc_info=True,
            )
            raise
