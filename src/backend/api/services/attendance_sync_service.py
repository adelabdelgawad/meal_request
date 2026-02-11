"""
Attendance Sync Service - Sync attendance data from TMS to MealRequestLineAttendance.

This service implements line-scoped sliding window sync:
- Only syncs attendance for existing MealRequestLine rows
- Never performs blind/full TMS attendance copy
- Groups by date for efficient batch queries
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.repositories.hris_repository import HRISRepository
from db.model import Employee, MealRequest, MealRequestLine, MealRequestLineAttendance
from db.schemas import AttendanceRecord

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of an attendance sync operation."""

    total: int = 0
    synced: int = 0
    unchanged: int = 0
    not_found: int = 0
    errors: int = 0


class AttendanceSyncService:
    """
    Service for syncing attendance data from TMS to MealRequestLineAttendance.

    Implements line-scoped sliding window sync:
    - Always derives what to sync from existing MealRequestLine rows
    - Never performs blind/full TMS attendance copy
    - Groups by date for efficient batch queries
    """

    def __init__(self):
        """Initialize the attendance sync service."""
        self._hris_repo = HRISRepository(self.session)

    async def sync_sliding_window(
        self,
        session: AsyncSession,
        hris_session: AsyncSession,
        months_back: int = 2,
    ) -> SyncResult:
        """
        Sliding window sync - re-syncs attendance for MealRequestLines in date range.

        Algorithm:
        1. Calculate date range: (today - N months) to today
        2. Get all MealRequestLines in date range (line-scoped!)
        3. Group by (date, employee_codes) for batch queries
        4. For each date:
           a. Collect employee_codes from MealRequestLines on that date
           b. Query TMS only for those employee_codes
           c. Compare with local MealRequestLineAttendance data
           d. Upsert only changed records
        5. Return: {synced, unchanged, not_found, errors}

        Args:
            session: Local database AsyncSession
            hris_session: HRIS database AsyncSession (TMS)
            months_back: Number of months to look back (default: 2)

        Returns:
            SyncResult with counts of synced, unchanged, not_found, errors
        """
        result = SyncResult()

        try:
            # Calculate date range
            today = date.today()
            start_date = today - timedelta(days=months_back * 30)

            logger.info(
                f"Starting attendance sync for date range: {start_date} to {today}"
            )

            # Get all MealRequestLines in date range with their attendance relationship
            # IMPORTANT: Filter by MealRequest.request_time (not MealRequestLine.created_at)
            # This ensures we only sync lines from recent meal requests (last 2 months)
            stmt = (
                select(MealRequestLine)
                .join(MealRequestLine.meal_request)
                .options(
                    selectinload(MealRequestLine.attendance),
                    selectinload(MealRequestLine.meal_request)
                )
                .where(~MealRequestLine.is_deleted)
                .where(MealRequest.request_time >= start_date)
            )
            db_result = await session.execute(stmt)
            request_lines = db_result.scalars().all()

            if not request_lines:
                logger.info("No MealRequestLines found in date range")
                return result

            result.total = len(request_lines)
            logger.info(f"✅ Found {result.total} MealRequestLines to sync from date range {start_date} to {today}")

            # Debug logging for the meal request lines
            logger.info("📊 Sample MealRequestLines (showing first 10):")
            for i, rl in enumerate(
                request_lines[:10]
            ):  # Log first 10 for debugging
                request_date = (
                    rl.meal_request.request_time.date()
                    if rl.meal_request and rl.meal_request.request_time
                    else "N/A"
                )
                logger.info(
                    f"  Line {i+1}: id={rl.id}, employee_code={rl.employee_code}, "
                    f"request_date={request_date}, created_at={rl.created_at.date()}"
                )
            if len(request_lines) > 10:
                logger.info(f"  ... and {len(request_lines) - 10} more lines")

            # Group by date (using request_time date as attendance_date)
            # CRITICAL: Use meal_request.request_time (NOT created_at) for TMS matching
            lines_by_date: Dict[date, List[MealRequestLine]] = defaultdict(
                list
            )
            for rl in request_lines:
                # Use request_time date from parent MealRequest as the attendance date
                # This is the actual date of the meal request, which matches TMS attendance records
                attendance_date = (
                    rl.meal_request.request_time.date()
                    if rl.meal_request and rl.meal_request.request_time
                    else today
                )
                lines_by_date[attendance_date].append(rl)

            # Process each date
            logger.info(f"📅 Processing {len(lines_by_date)} unique dates with lines")
            for target_date, lines in lines_by_date.items():
                logger.info(f"🔄 Processing date {target_date} with {len(lines)} lines")
                try:
                    synced, unchanged, not_found = (
                        await self._fetch_and_compare(
                            session, hris_session, lines, target_date
                        )
                    )
                    result.synced += synced
                    result.unchanged += unchanged
                    result.not_found += not_found
                    logger.info(
                        f"  ✅ Date {target_date}: synced={synced}, "
                        f"unchanged={unchanged}, not_found={not_found}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error syncing date {target_date}: {e}")
                    result.errors += len(lines)

            # Commit all changes
            await session.commit()

            logger.info(
                f"🎉 Attendance sync complete: {result.synced}/{result.total} synced, "
                f"{result.unchanged} unchanged, {result.not_found} not found, "
                f"{result.errors} errors"
            )

        except Exception as e:
            logger.error(f"Error during attendance sync: {e}")
            await session.rollback()
            raise

        return result

    async def sync_for_request_lines(
        self,
        session: AsyncSession,
        hris_session: AsyncSession,
        meal_request_line_ids: List[int],
    ) -> SyncResult:
        """
        Sync attendance only for the given MealRequestLine IDs.

        Targeted sync variant for:
        - Per-request sync (when viewing details)
        - Manual admin trigger for specific lines

        Algorithm:
        1. Load MealRequestLine rows by ID
        2. Group by (attendance_date, employee_code)
        3. Query TMS only for those pairs
        4. Upsert MealRequestLineAttendance records

        Args:
            session: Local database AsyncSession
            hris_session: HRIS database AsyncSession (TMS)
            meal_request_line_ids: List of MealRequestLine IDs to sync

        Returns:
            SyncResult with counts of synced, unchanged, not_found, errors
        """
        result = SyncResult()

        if not meal_request_line_ids:
            return result

        try:
            # Load MealRequestLines by IDs with their attendance relationship
            # Also load meal_request to get request_time for TMS matching
            stmt = (
                select(MealRequestLine)
                .options(
                    selectinload(MealRequestLine.attendance),
                    selectinload(MealRequestLine.meal_request)
                )
                .where(MealRequestLine.id.in_(meal_request_line_ids))
                .where(~MealRequestLine.is_deleted)
            )
            db_result = await session.execute(stmt)
            request_lines = list(db_result.scalars().all())

            if not request_lines:
                logger.info("No MealRequestLines found for given IDs")
                return result

            result.total = len(request_lines)
            logger.info(f"✅ Found {result.total} MealRequestLines for targeted sync")

            # Group by date (using request_time from parent MealRequest)
            lines_by_date: Dict[date, List[MealRequestLine]] = defaultdict(
                list
            )
            for rl in request_lines:
                # Use request_time date from parent MealRequest (not created_at)
                attendance_date = (
                    rl.meal_request.request_time.date()
                    if rl.meal_request and rl.meal_request.request_time
                    else date.today()
                )
                lines_by_date[attendance_date].append(rl)

            # Process each date
            logger.info(f"📅 Processing {len(lines_by_date)} unique dates")
            for target_date, lines in lines_by_date.items():
                logger.info(f"🔄 Processing date {target_date} with {len(lines)} lines")
                try:
                    synced, unchanged, not_found = (
                        await self._fetch_and_compare(
                            session, hris_session, lines, target_date
                        )
                    )
                    result.synced += synced
                    result.unchanged += unchanged
                    result.not_found += not_found
                    logger.info(
                        f"  ✅ Date {target_date}: synced={synced}, "
                        f"unchanged={unchanged}, not_found={not_found}"
                    )
                except Exception as e:
                    logger.error(f"❌ Error syncing date {target_date}: {e}")
                    result.errors += len(lines)

            # Commit all changes
            await session.commit()
            logger.info(f"🎉 Targeted sync complete: {result.synced}/{result.total} synced")

        except Exception as e:
            logger.error(f"Error during line-specific attendance sync: {e}")
            await session.rollback()
            raise

        return result

    async def _fetch_and_compare(
        self,
        session: AsyncSession,
        hris_session: AsyncSession,
        request_lines: List[MealRequestLine],
        target_date: date,
    ) -> Tuple[int, int, int]:
        """
        Fetch TMS data and compare with local.

        Args:
            session: Local database AsyncSession
            hris_session: HRIS database AsyncSession (TMS)
            request_lines: List of MealRequestLine objects to process
            target_date: Date to fetch attendance for

        Returns:
            Tuple of (synced_count, unchanged_count, not_found_count)
        """
        synced = 0
        unchanged = 0
        not_found = 0

        # Get unique employee codes from request lines
        employee_codes = list(
            set(
                rl.employee_code
                for rl in request_lines
                if rl.employee_code is not None
            )
        )

        # Debug logging for employee codes
        logger.info(f"📋 Processing {len(request_lines)} lines for date {target_date}")
        logger.info(f"👥 Found {len(employee_codes)} unique employee codes: {employee_codes[:10]}{'...' if len(employee_codes) > 10 else ''}")

        if not employee_codes:
            logger.warning(f"No employee codes found for date {target_date}")
            return synced, unchanged, len(request_lines)

        # Convert employee codes to HRIS IDs by querying local Employee table
        # The TMS database expects the original HRIS EmployeeId
        employee_stmt = select(Employee).where(
            Employee.code.in_(employee_codes)
        )
        employee_result = await session.execute(employee_stmt)
        employees = employee_result.scalars().all()

        # Create mapping: Employee code -> Employee ID (which is the HRIS ID)
        # Note: Employee.id is the HRIS Employee ID (consolidated in migration)
        code_to_employee_id_mapping = {}
        for emp in employees:
            code_to_employee_id_mapping[emp.code] = emp.id

        # Get employee IDs (which are HRIS IDs) for TMS queries
        employee_ids = [
            code_to_employee_id_mapping[code]
            for code in employee_codes
            if code in code_to_employee_id_mapping
        ]

        # Debug logging for employee mapping
        logger.info(f"🔗 Mapped {len(employees)} employees from local DB")
        logger.info(f"🆔 Employee IDs for TMS query: {employee_ids[:10]}{'...' if len(employee_ids) > 10 else ''}")

        missing_codes = [code for code in employee_codes if code not in code_to_employee_id_mapping]
        if missing_codes:
            logger.warning(f"⚠️  Missing employee mappings for codes: {missing_codes}")

        if not employee_ids:
            logger.warning(f"No employee IDs found for codes {employee_codes}")
            return synced, unchanged, len(request_lines)

        # Batch query TMS - only for employees we care about
        logger.info(f"🔍 Querying TMS for {len(employee_ids)} employees on {target_date}")
        tms_data = await self._hris_repo.get_attendance_for_employees(
            hris_session, employee_ids, target_date
        )
        logger.info(f"📦 TMS query returned {len(tms_data)} attendance records")

        if tms_data:
            logger.info("📊 Sample TMS records (first 3):")
            for i, record in enumerate(tms_data[:3]):
                logger.info(
                    f"  Record {i+1}: employee_id={record.employee_id}, "
                    f"time_in={record.time_in}, time_out={record.time_out}, "
                    f"hours={record.working_hours}"
                )
        else:
            logger.warning(f"⚠️  No TMS attendance records found for date {target_date}!")

        # Build lookup: employee_id -> attendance
        tms_lookup: Dict[int, AttendanceRecord] = {
            a.employee_id: a for a in tms_data
        }

        # Compare and upsert into MealRequestLineAttendance
        for rl in request_lines:
            if rl.employee_code is None:
                not_found += 1
                continue

            # Get employee ID for this employee code (for TMS lookup)
            employee_id = code_to_employee_id_mapping.get(rl.employee_code)
            if employee_id is None:
                not_found += 1
                continue

            # Look up TMS record using employee ID
            tms_record = tms_lookup.get(employee_id)
            if tms_record is None:
                not_found += 1
                continue

            if self._has_changed(rl.attendance, tms_record):
                # Upsert into MealRequestLineAttendance
                attendance = rl.attendance
                if attendance is None:
                    attendance = MealRequestLineAttendance(
                        meal_request_line_id=rl.id,
                        employee_code=rl.employee_code,
                        attendance_date=target_date,
                    )
                    session.add(attendance)
                    rl.attendance = attendance

                attendance.attendance_in = tms_record.time_in
                attendance.attendance_out = tms_record.time_out

                # Calculate working hours: prefer TMS calculation, fallback to manual calculation
                calculated_hours = self._calculate_working_hours(
                    tms_record.time_in,
                    tms_record.time_out,
                    tms_record.working_hours
                )
                attendance.working_hours = calculated_hours
                attendance.attendance_synced_at = datetime.utcnow()
                synced += 1
            else:
                unchanged += 1

        # Summary logging
        logger.info(
            f"📈 Summary for {target_date}: {synced} synced, {unchanged} unchanged, "
            f"{not_found} not found (out of {len(request_lines)} lines)"
        )
        if not_found > 0:
            logger.warning(
                f"⚠️  {not_found} lines had no TMS attendance match on {target_date}"
            )

        return synced, unchanged, not_found

    def _calculate_working_hours(
        self,
        time_in: Optional[datetime],
        time_out: Optional[datetime],
        tms_working_hours: Optional[float] = None,
    ) -> Optional[Decimal]:
        """
        Calculate working hours from attendance times.

        Prefers TMS-provided working hours, but falls back to manual calculation
        if TMS value is missing but we have both time_in and time_out.

        Args:
            time_in: Clock-in datetime
            time_out: Clock-out datetime
            tms_working_hours: Working hours from TMS (if available)

        Returns:
            Working hours as Decimal, or None if cannot be calculated
        """
        # Prefer TMS-provided working hours if available
        if tms_working_hours is not None:
            return Decimal(str(tms_working_hours))

        # Fallback: Calculate from time_in and time_out if both are available
        if time_in is not None and time_out is not None:
            try:
                # Calculate duration in hours
                duration = time_out - time_in
                hours = duration.total_seconds() / 3600.0

                # Ensure hours is non-negative (handle edge cases)
                if hours < 0:
                    logger.warning(
                        f"Negative working hours calculated: time_in={time_in}, "
                        f"time_out={time_out}. Setting to 0."
                    )
                    hours = 0.0

                # Round to 2 decimal places for consistency with DB column precision
                return Decimal(str(round(hours, 2)))
            except Exception as e:
                logger.error(
                    f"Error calculating working hours from times: {e}. "
                    f"time_in={time_in}, time_out={time_out}"
                )
                return None

        # Cannot calculate - missing required data
        return None

    def _has_changed(
        self,
        local: Optional[MealRequestLineAttendance],
        tms: AttendanceRecord,
    ) -> bool:
        """
        Compare local attendance record with TMS data.

        Args:
            local: Local MealRequestLineAttendance record (may be None)
            tms: TMS AttendanceRecord

        Returns:
            True if data has changed and needs update
        """
        if local is None:
            return True

        # Compare times (handle timezone differences by comparing values)
        local_in = local.attendance_in
        local_out = local.attendance_out
        tms_in = tms.time_in
        tms_out = tms.time_out

        if local_in != tms_in or local_out != tms_out:
            return True

        # Compare working hours (calculate TMS hours using our calculation logic)
        local_hours = (
            float(local.working_hours)
            if local.working_hours is not None
            else None
        )

        # Calculate TMS hours using the same logic as during sync
        calculated_hours = self._calculate_working_hours(
            tms_in, tms_out, tms.working_hours
        )
        tms_hours = float(calculated_hours) if calculated_hours is not None else None

        if local_hours != tms_hours:
            return True

        return False
