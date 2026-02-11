import logging
import uuid
from datetime import datetime, timezone
from typing import Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.services import (
    DepartmentService,
    EmployeeService,
    HRISService,
    SecurityUserService,
    DepartmentAssignmentService,
    LogReplicationService,
)
from db.model import SecurityUser, User, Employee

logger = logging.getLogger(__name__)


async def precreate_user_accounts(
    session: AsyncSession
) -> Dict[str, int]:
    """
    Pre-create user accounts for HRIS employees without local accounts.

    This ensures department assignments can be created during sync, even for
    employees who haven't logged in yet. Created users are inactive until first login.

    Reads SecurityUser records from database after linking phase to get employee_id.

    Args:
        session: AsyncSession for local database

    Returns:
        Dict with stats: {"created": int, "skipped": int, "errors": int}
    """
    from api.repositories import UserRepository
    from sqlalchemy import select

    user_repo = UserRepository()
    stats = {"created": 0, "skipped": 0, "errors": 0}

    # Read SecurityUser records from database (after linking phase)
    result = await session.execute(
        select(SecurityUser).where(SecurityUser.employee_id.isnot(None))
    )
    linked_security_users = result.scalars().all()

    logger.info(f"Found {len(linked_security_users)} SecurityUsers with employee links")

    for security_user in linked_security_users:
        # Capture attributes BEFORE try block to avoid lazy loading issues
        username = security_user.user_name
        employee_id = security_user.employee_id

        try:
            # Check if user already exists by username
            existing_user = await user_repo.get_by_username(session, username)

            if existing_user:
                stats["skipped"] += 1
                logger.debug(f"User already exists: {username}")
                continue

            # Check if user already exists by employee_id (to avoid duplicate key error)
            if employee_id:
                existing_by_emp_id = await session.execute(
                    select(User).where(User.employee_id == employee_id)
                )
                if existing_by_emp_id.scalar_one_or_none():
                    stats["skipped"] += 1
                    logger.debug(f"User with employee_id={employee_id} already exists, skipping {username}")
                    continue

            # Create stub user account
            new_user = User(
                id=str(uuid.uuid4()),
                username=username,
                employee_id=employee_id,
                is_domain_user=True,
                user_source='hris',  # Mark as HRIS-sourced user (Strategy A)
                is_active=False,  # Inactive until first login
                password=None,  # No password (LDAP auth only)
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            await user_repo.create(session, new_user)
            stats["created"] += 1

            logger.info(
                f"Pre-created user account: {username} "
                f"(employee_id={employee_id})"
            )

        except Exception as e:
            # Use captured variables, not object attributes (to avoid lazy loading)
            logger.error(
                f"Failed to pre-create user {username}: {e}",
                exc_info=True
            )
            stats["errors"] += 1

    return stats


async def replicate(hris_session: AsyncSession, session: AsyncSession, triggered_by_user_id: str = None) -> None:
    """
    Replicates HRIS data into the local database.

    This function fetches data from the HRIS system and populates the local replica tables.
    It deactivates existing data and inserts fresh data from HRIS.

    Args:
        hris_session (AsyncSession): The asynchronous session connected to the HRIS database.
        session (AsyncSession): The asynchronous session connected to the local database.
        triggered_by_user_id (str, optional): User ID who manually triggered the sync (None for scheduled tasks).
    """
    logger.info("Starting data replication from HRIS to local database.")

    # Initialize services
    hris_service = HRISService()
    department_service = DepartmentService()
    employee_service = EmployeeService()
    security_user_service = SecurityUserService()
    dept_assign_service = DepartmentAssignmentService()
    log_service = LogReplicationService()

    # Track timing and counts for logging
    start_time = datetime.now(timezone.utc)
    dept_created = 0
    emp_created = 0
    sec_user_created = 0
    dept_assign_created = 0
    dept_assign_reactivated = 0

    try:
        # Read data from the HRIS database using HRIS service
        departments = await hris_service.read_hris_departments(hris_session)
        employees = await hris_service.read_hris_active_employees(hris_session)
        security_users = await hris_service.read_hris_security_users(
            hris_session
        )
        department_assignments = await hris_service.read_hris_department_assignments(hris_session)

        # Check if all data was successfully read (allow None from HRIS if closed)
        if employees is not None and departments is not None and security_users is not None:
            logger.info(
                "All data read successfully from HRIS. Proceeding with data replication."
            )

            # Deactivate existing data before inserting new data
            logger.info(
                "Deactivating existing employees and security users..."
            )
            await hris_service.deactivate_all_employees(session)
            await hris_service.deactivate_all_security_users(session)
            # Deactivate ONLY HRIS-synced assignments, preserve manual ones
            hris_assign_deactivated = await hris_service.deactivate_hris_department_assignments(session)
            logger.info(f"Deactivated {hris_assign_deactivated} HRIS-synced department assignments.")

            # Pass 1: Insert departments and build ID mapping (without parent relationships)
            logger.info(
                f"Pass 1: Inserting {len(departments)} departments in the database."
            )
            dept_id_map = {}  # Map HRIS dept ID -> Local dept ID
            dept_parent_map = {}  # Map HRIS dept ID -> HRIS parent ID
            for dept_data in departments:
                try:
                    local_dept = await department_service.create_department(
                        session,
                        name_en=dept_data.name_en,
                        name_ar=dept_data.name_ar,
                        # parent_id will be set in Pass 2
                    )
                    dept_id_map[dept_data.id] = local_dept.id
                    dept_created += 1
                    # Store parent relationship for Pass 2
                    if dept_data.parent_id:
                        dept_parent_map[dept_data.id] = dept_data.parent_id
                except Exception as e:
                    logger.warning(
                        f"Failed to create department {dept_data.name_en}: {e}"
                    )
                    continue

            # Pass 2: Update parent relationships
            logger.info(
                f"Pass 2: Updating parent relationships for {len(dept_parent_map)} departments."
            )
            for hris_dept_id, hris_parent_id in dept_parent_map.items():
                try:
                    local_dept_id = dept_id_map.get(hris_dept_id)
                    local_parent_id = dept_id_map.get(hris_parent_id)

                    if local_dept_id and local_parent_id:
                        await department_service.update_department(
                            session,
                            department_id=local_dept_id,
                            parent_id=local_parent_id,
                        )
                    elif local_dept_id and not local_parent_id:
                        logger.warning(
                            f"Parent department {hris_parent_id} not found for department {hris_dept_id}. "
                            f"Setting as top-level department."
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to set parent for department {hris_dept_id}: {e}"
                    )
                    continue

            # Insert employees with mapped department IDs
            logger.info(
                f"Inserting {len(employees)} employees in the database."
            )
            for emp_data in employees:
                try:
                    # Map HRIS department_id to local department_id
                    local_dept_id = dept_id_map.get(emp_data.department_id)
                    if not local_dept_id:
                        logger.warning(
                            f"Skipping employee {emp_data.code}: department_id {emp_data.department_id} not found in mapping"
                        )
                        continue

                    await employee_service.create_employee(
                        session,
                        id=emp_data.id,  # Use HRIS ID as primary key
                        code=emp_data.code,
                        department_id=local_dept_id,
                        name_en=emp_data.name_en,
                        name_ar=emp_data.name_ar,
                        title=emp_data.title,
                    )
                    emp_created += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to create employee {emp_data.code}: {e}"
                    )
                    continue

            # Insert security users
            logger.info(
                f"Inserting {len(security_users)} security users in the database."
            )
            for sec_user_data in security_users:
                try:
                    await security_user_service.create_security_user(
                        session,
                        user_name=sec_user_data.user_name,
                        is_deleted=sec_user_data.is_deleted,
                        is_locked=sec_user_data.is_locked,
                    )
                    sec_user_created += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to create security user {sec_user_data.user_name}: {e}"
                    )
                    continue

            # Link security users to employees by matching HRIS IDs
            logger.info(
                f"Linking {len(security_users)} security users to employees by HRIS ID..."
            )
            sec_user_linked = await hris_service.sync_security_user_employee_links(session, security_users)
            logger.info(f"Successfully linked {sec_user_linked} security users to employees.")

            # Link application users to employees via SecurityUser
            logger.info(
                "Linking application users to employees via SecurityUser..."
            )
            logger.info(f"Total employees created: {emp_created}")
            user_linked = await hris_service.sync_user_employee_links(session)
            logger.info(f"Successfully linked {user_linked} users to employees.")
            logger.info(f"This means {emp_created - user_linked} employees have no linked user account.")

            # Phase 5.5: Pre-create user accounts for HRIS employees
            logger.info(
                "Pre-creating user accounts for HRIS employees without local accounts..."
            )
            precreate_stats = await precreate_user_accounts(session)
            logger.info(
                f"User pre-creation complete: {precreate_stats['created']} created, "
                f"{precreate_stats['skipped']} skipped, {precreate_stats['errors']} errors"
            )

            # Phase 6: Sync User.is_active status from SecurityUser
            # Strategy A: Only affects HRIS users, respects manual users and overrides
            logger.info(
                "Syncing User.is_active status from SecurityUser (Strategy A: Source Tracking)..."
            )
            user_sync_stats = await hris_service.sync_user_active_status_from_security_user(session)
            logger.info(
                f"User status sync complete: {user_sync_stats['deactivated']} deactivated, "
                f"{user_sync_stats['reactivated']} reactivated, "
                f"{user_sync_stats['skipped_manual']} manual users skipped, "
                f"{user_sync_stats['skipped_override']} override users skipped"
            )

            # Sync department assignments from HRIS TMS_ForwardEdit
            if department_assignments:
                logger.info(
                    f"Syncing {len(department_assignments)} department assignments from HRIS..."
                )
                logger.info(f"Available department mappings: {len(dept_id_map)} departments in ID map")
                logger.info(f"Sample of first 5 HRIS dept IDs in map: {list(dept_id_map.keys())[:5]}")

                assign_skipped = 0
                assign_no_user = 0
                assign_no_employee = 0
                assign_no_dept = 0

                # Log sample of assignment data
                logger.info("Sample of first 3 assignments to process:")
                for idx, assign_data in enumerate(department_assignments[:3]):
                    logger.info(
                        f"  Assignment {idx+1}: employee_id={assign_data.employee_id}, "
                        f"department_id={assign_data.department_id}"
                    )

                # Preload all employees with their users to avoid lazy loading issues
                # This is much more efficient than querying one-by-one
                unique_emp_ids = set(assign_data.employee_id for assign_data in department_assignments)
                logger.info(f"Preloading {len(unique_emp_ids)} unique employees with user relationships...")
                logger.info(f"Sample employee IDs to lookup: {sorted(list(unique_emp_ids))[:10]}")

                result = await session.execute(
                    select(Employee)
                    .where(Employee.id.in_(unique_emp_ids))
                    .options(selectinload(Employee.user))
                )
                employees_with_users = {emp.id: emp for emp in result.scalars().all()}
                logger.info(f"Preloaded {len(employees_with_users)} employees with users")

                # Diagnostic: Show which employee IDs are missing
                missing_emp_ids = unique_emp_ids - set(employees_with_users.keys())
                if missing_emp_ids:
                    logger.warning(
                        f"{len(missing_emp_ids)} employee IDs referenced in assignments but not found in Employee table"
                    )
                    logger.warning(f"Sample missing employee IDs: {sorted(list(missing_emp_ids))[:20]}")

                for idx, assign_data in enumerate(department_assignments):
                    try:
                        # Find the employee by ID (which is the HRIS employee ID)
                        # Note: Employee.id is the HRIS ID (consolidated in migration 2025_12_12_1300)
                        employee = employees_with_users.get(assign_data.employee_id)
                        if not employee:
                            if idx < 5:  # Log first 5 failures
                                logger.warning(
                                    f"Skipping assignment {idx+1}: Employee with ID {assign_data.employee_id} not found in local DB"
                                )
                            assign_no_employee += 1
                            assign_skipped += 1
                            continue

                        # Find the User linked to this employee (if any)
                        if not employee.user:
                            if assign_no_user < 5:  # Log first 5 failures
                                logger.warning(
                                    f"Skipping assignment {idx+1}: No user linked to employee {employee.id} "
                                    f"(code={employee.code}, employee_id from assignment={assign_data.employee_id})"
                                )
                            assign_no_user += 1
                            continue

                        # Find local department by HRIS ID
                        # Note: TMS_ForwardEdit.OrgUnitID maps to HRIS department ID
                        local_dept_id = dept_id_map.get(assign_data.department_id)
                        if not local_dept_id:
                            if assign_no_dept < 5:  # Log first 5 failures
                                logger.warning(
                                    f"Skipping assignment {idx+1}: Department with HRIS ID {assign_data.department_id} "
                                    f"not found in mapping (available: {len(dept_id_map)} depts)"
                                )
                            assign_no_dept += 1
                            assign_skipped += 1
                            continue

                        # Check if assignment already exists
                        existing = await dept_assign_service._repo.get_by_employee_and_department(
                            session, employee.user.id, local_dept_id
                        )

                        if existing:
                            if existing.is_synced_from_hris:
                                # Standard HRIS assignment - reactivate if needed
                                if not existing.is_active:
                                    await dept_assign_service.update_assignment(
                                        session,
                                        existing.id,
                                        updated_by_id=None,
                                        is_active=True,
                                    )
                                    dept_assign_reactivated += 1
                                    logger.debug(
                                        f"Reactivated HRIS assignment: User {employee.user.username} -> Dept {local_dept_id}"
                                    )
                            else:
                                # Manual assignment exists - HRIS takes precedence
                                # Convert manual assignment to HRIS-managed
                                logger.info(
                                    f"Converting manual→HRIS assignment: "
                                    f"User {employee.user.username} -> Dept {local_dept_id}"
                                )
                                await dept_assign_service.update_assignment(
                                    session,
                                    existing.id,
                                    updated_by_id=None,
                                    is_synced_from_hris=True,  # Convert to HRIS
                                    is_active=True,
                                )
                                dept_assign_reactivated += 1  # Count as reactivated
                        else:
                            # Create new HRIS assignment
                            await dept_assign_service.assign_user_to_department(
                                session=session,
                                user_id=employee.user.id,
                                department_id=local_dept_id,
                                created_by_id=None,  # HRIS records have no creator
                                is_synced_from_hris=True,
                            )
                            dept_assign_created += 1
                            logger.debug(
                                f"Created assignment: User {employee.user.username} -> Dept {local_dept_id}"
                            )

                    except Exception as e:
                        logger.warning(
                            f"Failed to sync department assignment (emp_id={assign_data.employee_id}, dept_id={assign_data.department_id}): {e}"
                        )
                        continue

                logger.info(
                    f"Department assignment sync completed: "
                    f"{dept_assign_created} created, {dept_assign_reactivated} reactivated, "
                    f"{assign_no_user} skipped (no user), {assign_no_employee} skipped (no employee), "
                    f"{assign_no_dept} skipped (no dept mapping), {assign_skipped} skipped (total)"
                )
            else:
                logger.info("No department assignments found in HRIS.")

            # Log replication summary
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            await log_service.log_replication(
                session=session,
                operation_type="hris_department_sync",
                is_successful=True,
                admin_id=triggered_by_user_id,
                records_processed=len(departments),
                records_created=dept_created,
                source_system="HRIS",
                duration_ms=duration_ms,
                result={"hris_dept_count": len(departments)},
            )
            await log_service.log_replication(
                session=session,
                operation_type="hris_employee_sync",
                is_successful=True,
                admin_id=triggered_by_user_id,
                records_processed=len(employees),
                records_created=emp_created,
                source_system="HRIS",
                duration_ms=duration_ms,
                result={"hris_emp_count": len(employees)},
            )
            await log_service.log_replication(
                session=session,
                operation_type="hris_security_user_sync",
                is_successful=True,
                admin_id=triggered_by_user_id,
                records_processed=len(security_users),
                records_created=sec_user_created,
                source_system="HRIS",
                duration_ms=duration_ms,
                result={
                    "hris_sec_user_count": len(security_users),
                    "sec_user_linked_count": sec_user_linked,
                    "user_linked_count": user_linked,
                },
            )

            # Log department assignment sync
            if department_assignments:
                await log_service.log_replication(
                    session=session,
                    operation_type="hris_department_assignment_sync",
                    is_successful=True,
                    admin_id=triggered_by_user_id,
                    records_processed=len(department_assignments),
                    records_created=dept_assign_created,
                    records_updated=dept_assign_reactivated,
                    source_system="HRIS",
                    duration_ms=duration_ms,
                    result={"hris_assign_count": len(department_assignments)},
                )

            logger.info("Data replication completed successfully.")

        else:
            logger.warning(
                "Failed to read all required data from HRIS. Data replication aborted."
            )
            duration_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            await log_service.log_replication(
                session=session,
                operation_type="hris_sync",
                is_successful=False,
                admin_id=triggered_by_user_id,
                source_system="HRIS",
                duration_ms=duration_ms,
                error_message="Failed to read all required data from HRIS",
            )

    except Exception as e:
        # Log any exceptions that occur during the replication process
        logger.error(
            "An error occurred during data replication.", exc_info=True
        )
        # Log replication failure
        duration_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        await log_service.log_replication(
            session=session,
            operation_type="hris_sync",
            is_successful=False,
            admin_id=triggered_by_user_id,
            source_system="HRIS",
            duration_ms=duration_ms,
            error_message=str(e),
        )
        # Re-raise to propagate failure to Celery task
        raise
