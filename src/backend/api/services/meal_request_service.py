"""Meal Request Service."""

import logging
from datetime import date, datetime
from typing import List, Optional, Tuple
from uuid import UUID

import pytz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.hris_repository import HRISRepository
from api.repositories.meal_request_line_repository import MealRequestLineRepository
from api.repositories.meal_request_repository import MealRequestRepository
from api.repositories.meal_request_status_repository import MealRequestStatusRepository
from api.repositories.meal_type_repository import MealTypeRepository
from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from db.models import Employee, MealRequest, MealRequestLine

logger = logging.getLogger(__name__)


class MealRequestService:
    """Service for meal request management."""

    def __init__(self):
        self._request_repo = MealRequestRepository()
        self._line_repo = MealRequestLineRepository()
        self._status_repo = MealRequestStatusRepository()
        self._meal_type_repo = MealTypeRepository()
        self._hris_repo = HRISRepository()

    async def create_request(
        self,
        session: AsyncSession,
        requester_id: UUID,
        meal_type_id: int,
        notes: Optional[str] = None,
        original_request_id: Optional[int] = None,
    ) -> MealRequest:
        """Create a new meal request.

        Args:
            session: Database session
            requester_id: UUID of the requester
            meal_type_id: ID of the meal type
            notes: Optional notes for the request
            original_request_id: ID of the original request if this is a copy
        """
        # Validate meal type exists
        meal_type = await self._meal_type_repo.get_by_id(session, meal_type_id)
        if not meal_type:
            raise NotFoundError(entity="MealType", identifier=meal_type_id)

        # Get pending status
        pending_status = await self._status_repo.get_by_name_en(session, "Pending")
        if not pending_status:
            raise NotFoundError(entity="MealRequestStatus", identifier="Pending")

        meal_request = MealRequest(
            requester_id=requester_id,
            meal_type_id=meal_type_id,
            status_id=pending_status.id,
            notes=notes,
            request_time=datetime.now(pytz.timezone("Africa/Cairo")),
            original_request_id=original_request_id,
        )

        return await self._request_repo.create(session, meal_request)

    async def get_request(self, session: AsyncSession, request_id: int) -> MealRequest:
        """Get a meal request by ID."""
        meal_request = await self._request_repo.get_by_id(session, request_id)
        if not meal_request:
            raise NotFoundError(entity="MealRequest", identifier=request_id)
        return meal_request

    async def list_requests(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        requester_id: Optional[UUID] = None,
        status_id: Optional[int] = None,
        meal_type_id: Optional[int] = None,
    ) -> Tuple[List[MealRequest], int]:
        """List meal requests with optional filtering."""
        return await self._request_repo.list(session, 
            page=page,
            per_page=per_page,
            requester_id=requester_id,
            status_id=status_id,
            meal_type_id=meal_type_id,
        )

    async def update_request_status(
        self,
        session: AsyncSession,
        request_id: int,
        status_id: int,
        closed_by_id: Optional[UUID] = None,
    ) -> MealRequest:
        """Update meal request status."""
        # Validate status exists
        status = await self._status_repo.get_by_id(session, status_id)
        if not status:
            raise NotFoundError(entity="MealRequestStatus", identifier=status_id)

        update_data = {"status_id": status_id}
        if closed_by_id:
            update_data["closed_by_id"] = closed_by_id
            update_data["closed_time"] = datetime.now(pytz.timezone("Africa/Cairo"))

        return await self._request_repo.update(session, request_id, update_data)

    async def add_line_to_request(
        self,
        session: AsyncSession,
        request_id: int,
        employee_id: int,
        attendance_time: Optional[datetime] = None,
        shift_hours: Optional[int] = None,
        notes: Optional[str] = None,
        hris_session: Optional[AsyncSession] = None,
    ):
        """Add a line item to a meal request.

        Args:
            session: Local database AsyncSession
            request_id: ID of the meal request
            employee_id: ID of the employee (department_id is auto-populated from employee)
            attendance_time: Optional attendance time (if not provided, will be fetched from HRIS)
            shift_hours: Optional shift hours
            notes: Optional notes
            hris_session: Optional HRIS AsyncSession for fetching real-time attendance

        Returns:
            Created MealRequestLine with attendance_time populated from HRIS if available
        """
        # Validate request exists
        meal_request = await self._request_repo.get_by_id(session, request_id)
        if not meal_request:
            raise NotFoundError(entity="MealRequest", identifier=request_id)

        # Fetch employee to get employee_code
        employee_stmt = select(Employee).where(Employee.id == employee_id)
        employee_result = await session.execute(employee_stmt)
        employee = employee_result.scalar_one_or_none()

        if not employee:
            raise NotFoundError(entity="Employee", identifier=employee_id)

        # If attendance_time not provided and hris_session is available, fetch from HRIS
        fetched_attendance_time = attendance_time
        if fetched_attendance_time is None and hris_session is not None:
            fetched_attendance_time = await self._fetch_attendance_from_hris(
                hris_session=hris_session,
                employee=employee,
                target_date=date.today(),
            )

        line = MealRequestLine(
            meal_request_id=request_id,
            employee_id=employee_id,
            employee_code=employee.code,  # Populate employee_code from Employee
            attendance_time=fetched_attendance_time,
            shift_hours=shift_hours,
            notes=notes,
            is_accepted=True,  # Default to accepted on creation
        )

        return await self._line_repo.create(session, line)

    async def _fetch_attendance_from_hris(
        self,
        hris_session: AsyncSession,
        employee: Employee,
        target_date: date,
    ) -> Optional[datetime]:
        """
        Fetch attendance sign-in time from HRIS TMS_Attendance table.

        This is a synchronous (blocking) operation that queries the real-time
        attendance system to determine if the employee has signed in today.

        Args:
            hris_session: HRIS database AsyncSession
            employee: Employee model instance
            target_date: Date to fetch attendance for (typically today)

        Returns:
            Sign-in datetime if found, None otherwise
        """
        try:
            # Query TMS_Attendance for sign-in time
            # employee.id is the HRIS employee ID (used as primary key)
            sign_in_time = await self._hris_repo.get_today_sign_in_time(
                session=hris_session,
                employee_id=employee.id,
                target_date=target_date,
            )

            if sign_in_time is None:
                logger.info(
                    f"No sign-in attendance found for employee {employee.id} "
                    f"(code: {employee.code}) on {target_date}"
                )
            else:
                logger.info(
                    f"Fetched sign-in time for employee {employee.id} "
                    f"(code: {employee.code}): {sign_in_time}"
                )

            return sign_in_time

        except Exception as e:
            # Log error but don't block meal request line creation
            logger.error(
                f"Error fetching attendance for employee {employee.id} "
                f"(code: {employee.code}): {str(e)}",
                exc_info=True
            )
            return None

    async def get_request_lines(self, session: AsyncSession, request_id: int):
        """Get all lines for a request."""
        return await self._line_repo.get_by_request(session, request_id)

    async def update_line(
        self,
        session: AsyncSession,
        line_id: int,
        is_accepted: Optional[bool] = None,
        notes: Optional[str] = None,
    ):
        """Update a meal request line."""
        update_data = {}
        if is_accepted is not None:
            update_data["is_accepted"] = is_accepted
        if notes is not None:
            update_data["notes"] = notes

        return await self._line_repo.update(session, line_id, update_data)

    async def delete_request_line(self, session: AsyncSession, line_id: int) -> None:
        """Delete a meal request line."""
        await self._line_repo.delete(session, line_id)

    async def copy_request(
        self,
        session: AsyncSession,
        source_request_id: int,
        requester_id: str,
    ) -> Tuple[MealRequest, int]:
        """
        Copy an existing meal request with all its lines.

        Creates a new meal request with the same meal type and lines as the source,
        but with fresh IDs and default values (Pending status, current timestamp).

        Prevents duplicate copies by tracking the original request ID. A request
        cannot be copied if there's already a pending copy of the same original.

        Args:
            session: Database session
            source_request_id: ID of the request to copy
            requester_id: UUID string of the current user (must match source requester)

        Returns:
            Tuple of (new_meal_request, lines_copied_count)

        Raises:
            NotFoundError: If source request doesn't exist
            AuthorizationError: If requester doesn't own the source request
            ValidationError: If source request is still pending or has a pending copy
        """
        # 1. Fetch source request
        source_request = await self._request_repo.get_by_id(session, source_request_id)
        if not source_request:
            raise NotFoundError(entity="MealRequest", identifier=source_request_id)

        # 2. Verify ownership - user can only copy their own requests
        if str(source_request.requester_id) != str(requester_id):
            raise AuthorizationError("You can only copy your own requests")

        # 3. Check status - cannot copy pending requests
        pending_status = await self._status_repo.get_by_name_en(session, "Pending")
        if source_request.status_id == pending_status.id:
            raise ValidationError(
                errors=[{"field": "status", "message": "Cannot copy a pending request"}],
                message="Cannot copy a request that is still pending. Please wait until it is processed."
            )

        # 4. Determine the original request ID for tracking copies
        # If source is already a copy, use its original_request_id
        # Otherwise, use the source's ID
        original_id = source_request.original_request_id or source_request_id

        # 5. Check if there's already a pending copy of this original
        existing_pending_copy = await self._request_repo.get_pending_copy(
            session, original_id, requester_id
        )
        if existing_pending_copy:
            raise ValidationError(
                errors=[{"field": "original_request_id", "message": "A pending copy already exists"}],
                message=f"A pending copy of this request already exists (Request #{existing_pending_copy.id}). "
                        "Please wait until it is processed before creating another copy."
            )

        # 6. Get source request lines
        source_lines = await self._line_repo.get_by_request(session, source_request_id)

        # 7. Create new request with default values and original_request_id
        new_request = await self.create_request(
            session=session,
            requester_id=requester_id,
            meal_type_id=source_request.meal_type_id,
            notes=source_request.notes,  # Copy notes from original
            original_request_id=original_id,  # Track the original request
        )

        # 8. Copy each non-deleted line with reset values
        lines_copied = 0
        for source_line in source_lines:
            if not source_line.is_deleted:
                await self.add_line_to_request(
                    session=session,
                    request_id=new_request.id,
                    employee_id=source_line.employee_id,
                    # Department accessed via employee.department relationship
                    attendance_time=None,  # Reset - will be synced later
                    shift_hours=None,  # Reset
                    notes=source_line.notes,  # Copy notes
                )
                lines_copied += 1

        return new_request, lines_copied

    async def get_meal_requests_for_details_page(
        self,
        session: AsyncSession,
        status_id: Optional[int] = None,
        requester_filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        department_ids: Optional[List[int]] = None,
        page: int = 1,
        page_size: int = 50
    ):
        """Get all meal requests with aggregated data for display.

        Args:
            department_ids: If provided (non-empty), only show meal requests that have
                           at least one line in these departments. If None or empty,
                           show all meal requests (no department restriction).
        """
        return await self._request_repo.read_meal_request_for_request_details_page(
            session,
            status_id=status_id,
            requester_filter=requester_filter,
            from_date=from_date,
            to_date=to_date,
            department_ids=department_ids,
            page=page,
            page_size=page_size
        )

    async def get_single_meal_request_summary(self, session: AsyncSession, meal_request_id: int):
        """Get a single meal request with aggregated data for display."""
        return await self._request_repo.read_single_meal_request_summary(session, meal_request_id)

    async def get_meal_request_stats(self, session: AsyncSession):
        """Get statistics about meal requests (counts by status)."""
        return await self._request_repo.get_status_counts(session)

    async def get_filtered_meal_request_stats(
        self,
        session: AsyncSession,
        requester_filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        department_ids: Optional[List[int]] = None,
    ):
        """Get statistics about meal requests with filters applied (excludes status filter).

        Args:
            department_ids: If provided (non-empty), only count meal requests that have
                           at least one line in these departments.
        """
        return await self._request_repo.get_filtered_status_counts(
            session,
            requester_filter=requester_filter,
            from_date=from_date,
            to_date=to_date,
            department_ids=department_ids,
        )

    async def get_meal_request_lines_for_request(self, session: AsyncSession, request_id: int):
        """Get meal request lines with employee and department details for a specific request."""
        return await self._line_repo.read_meal_request_line_for_requests_page(session, request_id)

    async def get_closed_accepted_requests_for_audit(
        self, session: AsyncSession, start_time: datetime, end_time: datetime
    ):
        """Get closed and accepted meal request lines for audit reporting."""
        return await self._line_repo.read_closed_accepted_requests_for_audit_page(
            session, start_time, end_time
        )

    async def get_closed_requests_with_accept_status(
        self, session: AsyncSession, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ):
        """Get closed requests with acceptance status for analysis."""
        return await self._line_repo.read_closed_requests_with_accept_status(
            session, start_time, end_time
        )

    async def update_meal_request_status(
        self, session: AsyncSession, meal_request_id: int, status_id: int, closed_by_id: str
    ):
        """Update meal request status with closed information."""
        return await self._request_repo.update_meal_request_status(
            session, meal_request_id, status_id, closed_by_id
        )

    async def create_meal_request(self, session: AsyncSession, meal_request_data):
        """Create a new meal request."""
        return await self._request_repo.create(session, meal_request_data)

    async def create_meal_request_line(self, session: AsyncSession, line_data):
        """Create a new meal request line."""
        return await self._line_repo.create(session, line_data)

    async def update_meal_request_line(
        self, session: AsyncSession, line_id: int, is_accepted: bool, notes: Optional[str] = None
    ):
        """Update meal request line status and notes."""
        update_data = {"is_accepted": is_accepted}
        if notes is not None:
            update_data["notes"] = notes
        return await self._line_repo.update(session, line_id, update_data)

    async def update_meal_order_line_status_by_meal_order(
        self, session: AsyncSession, meal_request_id: int, is_accepted: bool
    ):
        """Update all meal request lines status for a given meal request."""
        return await self._line_repo.update_meal_order_line_status_by_meal_order(
            session, meal_request_id, is_accepted
        )
