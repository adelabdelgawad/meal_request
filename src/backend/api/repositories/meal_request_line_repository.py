"""Meal Request Line Repository."""

from typing import List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DatabaseError, NotFoundError
from db.models import MealRequestLine, MealRequest, Employee, Department, MealType, User, MealRequestStatus
from utils.app_schemas import MealRequestLineResponse, RequestDataResponse, AuditRecordResponse


class MealRequestLineRepository:
    """Repository for MealRequestLine entity."""

    def __init__(self):
        pass

    async def create(self, session: AsyncSession, line: MealRequestLine) -> MealRequestLine:
        try:
            session.add(line)
            await session.flush()
            return line
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create meal request line: {str(e)}")

    async def get_by_id(self, session: AsyncSession, line_id: int) -> Optional[MealRequestLine]:
        result = await session.execute(
            select(MealRequestLine).where(
                MealRequestLine.id == line_id,
                MealRequestLine.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        meal_request_id: Optional[int] = None,
        employee_id: Optional[int] = None,
    ) -> Tuple[List[MealRequestLine], int]:
        from core.pagination import calculate_offset

        query = select(MealRequestLine).where(MealRequestLine.is_deleted == False)  # noqa: E712

        if meal_request_id:
            query = query.where(MealRequestLine.meal_request_id == meal_request_id)
        if employee_id:
            query = query.where(MealRequestLine.employee_id == employee_id)

        # Optimized count query


        count_query = select(func.count()).select_from((query).subquery())


        count_result = await session.execute(count_query)


        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(
            query.offset(offset).limit(per_page)
        )
        return result.scalars().all(), total

    async def get_by_request(self, session: AsyncSession, request_id: int) -> List[MealRequestLine]:
        """Get all lines for a specific request."""
        result = await session.execute(
            select(MealRequestLine).where(
                MealRequestLine.meal_request_id == request_id,
                MealRequestLine.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalars().all()

    async def update(self, session: AsyncSession, line_id: int, line_data: dict) -> MealRequestLine:
        line = await self.get_by_id(session, line_id)
        if not line:
            raise NotFoundError(entity="MealRequestLine", identifier=line_id)

        try:
            for key, value in line_data.items():
                if value is not None and hasattr(line, key):
                    setattr(line, key, value)

            await session.flush()
            return line
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update meal request line: {str(e)}")

    async def delete(self, session: AsyncSession, line_id: int) -> None:
        line = await self.get_by_id(session, line_id)
        if not line:
            raise NotFoundError(entity="MealRequestLine", identifier=line_id)

        await session.delete(line)
        await session.flush()

    # Specialized CRUD compatibility methods
    async def read_meal_request_line_for_requests_page(
        self, session: AsyncSession, request_id: int
    ) -> Optional[List[MealRequestLineResponse]]:
        """Retrieve meal request lines for a specific request with detailed information."""
        from db.models import MealRequestLineAttendance
        from utils.app_schemas import TmsAttendanceResponse

        stmt = (
            select(
                MealRequestLine.id,
                Employee.code,
                Employee.name_en,
                Employee.name_ar,
                Employee.title,
                Department.name_en.label("department_en"),
                Department.name_ar.label("department_ar"),
                MealRequestLine.shift_hours,
                MealRequestLine.attendance_time,
                MealRequestLine.is_accepted,
                MealType.name_ar.label("meal_type"),
                MealRequestLine.notes,
                MealRequestLineAttendance.attendance_in,
                MealRequestLineAttendance.attendance_out,
                MealRequestLineAttendance.working_hours,
                MealRequestLineAttendance.attendance_synced_at,
            )
            .join(MealRequest, MealRequestLine.meal_request)
            .join(Employee, MealRequestLine.employee)
            .join(Department, Employee.department)
            .join(MealType, MealRequest.meal_type)
            .outerjoin(MealRequestLineAttendance, MealRequestLine.id == MealRequestLineAttendance.meal_request_line_id)
            .where(
                MealRequest.id == request_id,
                MealRequestLine.is_deleted == False,  # noqa: E712
            )
        )

        try:
            result = await session.execute(stmt)
            meal_request_lines = result.all()

            if not meal_request_lines:
                return []

            return [
                MealRequestLineResponse(
                    request_line_id=line.id,
                    code=line.code,
                    name_en=line.name_en,
                    name_ar=line.name_ar,
                    title=line.title,
                    department_en=line.department_en,
                    department_ar=line.department_ar,
                    shift_hours=line.shift_hours,
                    sign_in_time=line.attendance_time,
                    accepted=line.is_accepted,
                    notes=line.notes,
                    meal_type=line.meal_type,
                    tms_attendance=(
                        TmsAttendanceResponse(
                            attendance_in=line.attendance_in,
                            attendance_out=line.attendance_out,
                            working_hours=float(line.working_hours) if line.working_hours else None,
                            attendance_synced_at=line.attendance_synced_at,
                        )
                        if line.attendance_in is not None or line.attendance_out is not None
                        else None
                    ),
                )
                for line in meal_request_lines
            ]
        except Exception as e:
            raise DatabaseError(f"Failed to read meal request lines: {str(e)}")

    async def read_closed_requests_with_accept_status(
        self, session: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[RequestDataResponse]:
        """Fetch accepted meal requests for closed requests, grouped by department."""
        import logging
        logger = logging.getLogger(__name__)

        stmt = (
            select(
                Department.name_ar.label("name"),
                func.count(MealRequestLine.id).label("accepted_requests"),
            )
            .select_from(Department)
            .join(Employee, Department.id == Employee.department_id)
            .join(MealRequestLine, MealRequestLine.employee_id == Employee.id)
            .join(MealRequest, MealRequestLine.meal_request_id == MealRequest.id)
            .where(
                MealRequestLine.is_accepted,
                MealRequest.closed_time.isnot(None),
                MealRequestLine.is_deleted == False,  # noqa: E712
            )
            .group_by(Department.name_ar)
        )

        if start_time and end_time:
            stmt = stmt.where(
                MealRequest.request_time.between(start_time, end_time)
            )

        try:
            logger.info(f"Fetching closed requests with accept status - start_time: {start_time}, end_time: {end_time}")
            result = await session.execute(stmt)
            rows = result.fetchall()
            logger.info(f"Found {len(rows)} departments with accepted requests")

            response_data = [RequestDataResponse.model_validate(row) for row in rows]
            logger.info(f"Returning {len(response_data)} request data responses")
            return response_data
        except Exception as e:
            logger.error(f"Failed to read closed requests: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to read closed requests: {str(e)}")

    async def read_closed_accepted_requests_for_audit_page(
        self, session: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditRecordResponse]:
        """Fetch accepted meal request lines for closed requests with audit details including attendance."""
        from db.models import MealRequestLineAttendance

        stmt = (
            select(
                MealRequestLine.id,
                Employee.code,
                Employee.name_en.label("employee_name_en"),
                Employee.name_ar.label("employee_name_ar"),
                Employee.title,
                Department.name_en.label("department_en"),
                Department.name_ar.label("department_ar"),
                User.full_name.label("requester_en"),  # Using full_name for both locales
                User.full_name.label("requester_ar"),
                User.title.label("requester_title"),
                MealType.name_ar.label("meal_type"),
                MealRequestLine.notes,
                MealRequest.request_time,
                MealRequestLineAttendance.attendance_in.label("in_time"),
                MealRequestLineAttendance.attendance_out.label("out_time"),
                MealRequestLineAttendance.working_hours,
            )
            .join(Employee, MealRequestLine.employee_id == Employee.id)
            .join(Department, Employee.department_id == Department.id)
            .join(MealRequest, MealRequestLine.meal_request_id == MealRequest.id)
            .join(User, MealRequest.requester_id == User.id)
            .join(MealType, MealRequest.meal_type_id == MealType.id)
            .outerjoin(MealRequestLineAttendance, MealRequestLine.id == MealRequestLineAttendance.meal_request_line_id)
            .where(
                MealRequestLine.is_accepted,
                MealRequest.status_id == 2,
                MealRequestLine.is_deleted == False,  # noqa: E712
            )
            .order_by(MealRequest.request_time)
        )

        if start_time and end_time:
            stmt = stmt.where(
                MealRequest.request_time.between(start_time, end_time)
            )
        elif start_time:
            stmt = stmt.where(MealRequest.request_time >= start_time)
        elif end_time:
            stmt = stmt.where(MealRequest.request_time <= end_time)

        try:
            result = await session.execute(stmt)
            records = result.fetchall()

            return [AuditRecordResponse.model_validate(row) for row in records]
        except Exception as e:
            raise DatabaseError(f"Failed to read audit records: {str(e)}")

    async def update_meal_order_line_status_by_meal_order(
        self, session: AsyncSession, meal_order_id: int, accepted: bool
    ) -> Optional[List[MealRequestLine]]:
        """Update accepted status for all lines in a meal order."""
        try:
            stmt = (
                select(MealRequestLine)
                .join(MealRequest.meal_request_lines)
                .where(
                    MealRequest.id == meal_order_id,
                    MealRequestLine.is_deleted == False,  # noqa: E712
                )
            )

            result = await session.execute(stmt)
            meal_order_lines = result.scalars().all()

            if meal_order_lines:
                for line in meal_order_lines:
                    line.is_accepted = accepted

                await session.flush()
                return meal_order_lines

            return None
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update meal order lines: {str(e)}")

    async def soft_delete_line(
        self,
        session: AsyncSession,
        line_id: int,
        request_id: int,
        user_id: str,
    ) -> MealRequestLine:
        """
        Soft delete a meal request line with parent request validation.

        This method implements a secure soft delete with the following guarantees:
        1. Locks the parent MealRequest to validate its status
        2. Validates user owns the parent request
        3. Validates parent request status is PENDING
        4. Validates line belongs to the specified request
        5. Soft deletes only the line (not the entire request)

        Args:
            session: Database session (must be within a transaction)
            line_id: ID of the line to delete
            request_id: ID of the parent meal request
            user_id: UUID of the user performing the deletion

        Returns:
            The soft-deleted MealRequestLine instance

        Raises:
            NotFoundError: If line or request doesn't exist
            AuthorizationError: If user doesn't own the parent request
            ValidationError: If parent request status is not PENDING or line already deleted
            DatabaseError: If deletion fails
        """
        from core.exceptions import AuthorizationError, ValidationError

        try:
            # Step 1: Lock the parent request to validate status
            stmt = (
                select(MealRequest)
                .where(MealRequest.id == request_id)
                .with_for_update()  # 🔒 Lock parent request
            )
            result = await session.execute(stmt)
            request = result.scalar_one_or_none()

            # Step 2: Validate parent request exists
            if not request:
                raise NotFoundError(entity="MealRequest", identifier=request_id)

            # Step 3: Validate ownership
            if request.requester_id != user_id:
                raise AuthorizationError(
                    "You are not authorized to delete lines from this meal request"
                )

            # Step 4: Get PENDING status dynamically
            from api.repositories.meal_request_status_repository import MealRequestStatusRepository
            status_repo = MealRequestStatusRepository()
            pending_status = await status_repo.get_by_name_en(session, "Pending")

            if not pending_status:
                raise DatabaseError("PENDING status not found in database")

            # Step 5: Validate parent request status is PENDING
            if request.status_id != pending_status.id:
                # Get current status name for error message
                current_status = await session.get(MealRequestStatus, request.status_id)
                status_name = current_status.name_en if current_status else "Unknown"
                raise ValidationError(
                    f"Cannot delete line from meal request with status: {status_name}. "
                    "Only lines from PENDING requests can be deleted."
                )

            # Step 6: Get the line
            line = await session.get(MealRequestLine, line_id)
            if not line:
                raise NotFoundError(entity="MealRequestLine", identifier=line_id)

            # Step 7: Validate line belongs to the request
            if line.meal_request_id != request_id:
                raise ValidationError(
                    f"Line {line_id} does not belong to request {request_id}"
                )

            # Step 8: Check if already deleted
            if line.is_deleted:
                raise ValidationError("Meal request line has already been deleted")

            # Step 9: Soft delete the line
            line.is_deleted = True
            line.updated_at = datetime.now(timezone.utc)

            await session.flush()
            return line

        except (NotFoundError, AuthorizationError, ValidationError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to soft delete meal request line: {str(e)}")
