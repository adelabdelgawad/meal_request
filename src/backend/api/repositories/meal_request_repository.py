"""Meal Request Repository."""

import re
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timezone

from core.exceptions import DatabaseError, NotFoundError
from db.models import (
    Employee,
    MealRequest,
    MealRequestLine,
    MealRequestStatus,
    MealType,
    User,
)
from utils.app_schemas import MealRequestSummary

# UUID pattern for requester filter detection
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class MealRequestRepository:
    """Repository for MealRequest entity."""

    def __init__(self):
        pass

    async def create(
        self, session: AsyncSession, meal_request: MealRequest
    ) -> MealRequest:
        try:
            session.add(meal_request)
            await session.flush()
            return meal_request
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to create meal request: {str(e)}")

    async def get_by_id(
        self, session: AsyncSession, request_id: int
    ) -> Optional[MealRequest]:
        result = await session.execute(
            select(MealRequest).where(
                MealRequest.id == request_id,
                MealRequest.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        requester_id: Optional[UUID] = None,
        status_id: Optional[int] = None,
        meal_type_id: Optional[int] = None,
    ) -> Tuple[List[MealRequest], int]:
        from core.pagination import calculate_offset

        query = select(MealRequest).where(MealRequest.is_deleted == False)  # noqa: E712

        if requester_id:
            query = query.where(MealRequest.requester_id == requester_id)
        if status_id:
            query = query.where(MealRequest.status_id == status_id)
        if meal_type_id:
            query = query.where(MealRequest.meal_type_id == meal_type_id)

        # Optimized count query

        count_query = select(func.count()).select_from((query).subquery())

        count_result = await session.execute(count_query)

        total = count_result.scalar() or 0

        offset = calculate_offset(page, per_page)
        result = await session.execute(query.offset(offset).limit(per_page))
        return result.scalars().all(), total

    async def update(
        self, session: AsyncSession, request_id: int, request_data: dict
    ) -> MealRequest:
        meal_request = await self.get_by_id(session, request_id)
        if not meal_request:
            raise NotFoundError(entity="MealRequest", identifier=request_id)

        try:
            for key, value in request_data.items():
                if value is not None and hasattr(meal_request, key):
                    setattr(meal_request, key, value)

            await session.flush()
            return meal_request
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to update meal request: {str(e)}")

    async def delete(self, session: AsyncSession, request_id: int) -> None:
        meal_request = await self.get_by_id(session, request_id)
        if not meal_request:
            raise NotFoundError(entity="MealRequest", identifier=request_id)

        await session.delete(meal_request)
        await session.flush()

    # Specialized CRUD compatibility methods
    async def create_meal_request_status(
        self, session: AsyncSession, name_en: str, name_ar: str
    ) -> Optional[MealRequestStatus]:
        """Create or update a meal request status."""
        try:
            existing = await self.get_meal_request_status_by_name_en(
                session, name_en
            )
            if existing:
                return existing

            new_status = MealRequestStatus(name_en=name_en, name_ar=name_ar)
            session.add(new_status)
            await session.flush()
            return new_status
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                f"Failed to create meal request status: {str(e)}"
            )

    async def get_meal_request_status_by_name_en(
        self, session: AsyncSession, status_name: str
    ) -> Optional[MealRequestStatus]:
        """Get meal request status by English name (case-insensitive)."""
        result = await session.execute(
            select(MealRequestStatus).where(
                func.lower(MealRequestStatus.name_en) == status_name.lower()
            )
        )
        return result.scalar_one_or_none()

    async def get_meal_request_status_by_name(
        self, session: AsyncSession, status_name: str
    ) -> Optional[MealRequestStatus]:
        """Get meal request status by name in either language (case-insensitive)."""
        result = await session.execute(
            select(MealRequestStatus).where(
                (func.lower(MealRequestStatus.name_en) == status_name.lower())
                | (
                    func.lower(MealRequestStatus.name_ar)
                    == status_name.lower()
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_meal_request_status(
        self,
        session: AsyncSession,
        meal_request_id: int,
        status_id: int,
        closed_by_id: str,
    ) -> Optional[MealRequest]:
        """Update meal request status and closed information."""
        try:
            meal_request = await self.get_by_id(session, meal_request_id)
            if not meal_request:
                return None

            # Verify that the user exists before setting closed_by_id
            from db.models import User

            user = await session.get(User, closed_by_id)
            if not user:
                raise DatabaseError(f"User with ID {closed_by_id} not found")

            meal_request.status_id = status_id
            meal_request.closed_by_id = closed_by_id
            meal_request.closed_time = datetime.now()

            await session.flush()
            return meal_request
        except Exception as e:
            await session.rollback()
            raise DatabaseError(
                f"Failed to update meal request status: {str(e)}"
            )

    async def read_meal_request_for_request_details_page(
        self,
        session: AsyncSession,
        status_id: Optional[int] = None,
        requester_filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        department_ids: Optional[List[int]] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[MealRequestSummary], int]:
        """Fetch meal requests with aggregated data for display. Returns (items, total_count).

        Args:
            department_ids: If provided (non-empty), only show meal requests that have
                           at least one line in these departments. If None or empty,
                           show all meal requests (no department restriction).
        """
        from datetime import datetime

        stmt = (
            select(
                MealRequest.id.label("meal_request_id"),
                MealRequestStatus.id.label("status_id"),
                MealRequestStatus.name_en.label("status_name_en"),
                MealRequestStatus.name_ar.label("status_name_ar"),
                User.username.label("requester_name"),
                User.title.label("requester_title"),
                MealRequest.request_time,
                MealRequest.notes,
                MealRequest.closed_time,
                MealType.name_en.label("meal_type_en"),
                MealType.name_ar.label("meal_type_ar"),
                func.count(MealRequestLine.id).label("total_request_lines"),
                func.sum(
                    case((MealRequestLine.is_accepted, 1), else_=0)
                ).label("accepted_request_lines"),
            )
            .join(MealRequestStatus, MealRequest.status_id == MealRequestStatus.id)
            .join(User, MealRequest.requester_id == User.id)
            .join(MealType, MealRequest.meal_type_id == MealType.id)
            .outerjoin(
                MealRequestLine,
                (MealRequestLine.meal_request_id == MealRequest.id) &
                (MealRequestLine.is_deleted == False),  # noqa: E712
            )
        )

        # Apply filters
        filters = [
            MealRequest.request_time.isnot(None),
            MealRequest.is_deleted == False,  # noqa: E712 - Exclude soft-deleted requests
        ]

        # Status filter by ID - if provided, use it explicitly
        if status_id:
            filters.append(MealRequestStatus.id == status_id)
        else:
            # Only exclude "On Progress" status (4) when NO status filter is provided
            # These requests are still being processed asynchronously
            filters.append(MealRequestStatus.id != 4)

        # Department filter - if user has department assignments, filter by them
        # Empty list or None means no restriction (see all departments)
        if department_ids:
            # Join Employee through MealRequestLine to filter by department
            stmt = stmt.outerjoin(
                Employee, MealRequestLine.employee_id == Employee.id
            )
            # Only show meal requests that have at least one line in the user's departments
            filters.append(Employee.department_id.in_(department_ids))

        # Requester filter - check if it's a UUID (exact match on requester_id) or a name search
        if requester_filter and requester_filter.strip():
            if UUID_PATTERN.match(requester_filter.strip()):
                # Exact match on requester_id (for /my-requests endpoint)
                filters.append(
                    MealRequest.requester_id == requester_filter.strip()
                )
            else:
                # Partial match on username (for search functionality)
                filters.append(User.username.ilike(f"%{requester_filter}%"))

        # Date filters
        if from_date:
            try:
                from_dt = datetime.fromisoformat(
                    from_date.replace("Z", "+00:00")
                )
                filters.append(MealRequest.request_time >= from_dt)
            except ValueError:
                pass  # Invalid date format, skip filter

        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
                filters.append(MealRequest.request_time <= to_dt)
            except ValueError:
                pass  # Invalid date format, skip filter

        stmt = (
            stmt.where(*filters)
            .group_by(
                MealRequest.id,
                MealRequestStatus.id,
                MealRequestStatus.name_en,
                MealRequestStatus.name_ar,
                User.username,
                User.title,
                MealRequest.notes,
                MealType.name_en,
                MealType.name_ar,
                MealRequest.request_time,
                MealRequest.closed_time,
            )
            .having(func.count(MealRequestLine.id) > 0)  # Only show requests with active lines
            .order_by(MealRequest.id.desc())
        )

        try:
            # Get total count (before pagination)
            count_stmt = select(func.count()).select_from(stmt.alias())
            total_count_result = await session.execute(count_stmt)
            total_count = total_count_result.scalar() or 0

            # Apply pagination
            offset = (page - 1) * page_size
            stmt = stmt.limit(page_size).offset(offset)

            # Execute query
            result = await session.execute(stmt)
            meal_requests = result.all()

            if not meal_requests:
                return [], total_count

            return [
                MealRequestSummary(**request._asdict())
                for request in meal_requests
            ], total_count
        except Exception as e:
            raise DatabaseError(f"Failed to read meal requests: {str(e)}")

    async def read_single_meal_request_summary(
        self, session: AsyncSession, meal_request_id: int
    ) -> Optional[MealRequestSummary]:
        """Fetch a single meal request with aggregated data for display."""
        stmt = (
            select(
                MealRequest.id.label("meal_request_id"),
                MealRequestStatus.id.label("status_id"),
                MealRequestStatus.name_en.label("status_name_en"),
                MealRequestStatus.name_ar.label("status_name_ar"),
                User.username.label("requester_name"),
                User.title.label("requester_title"),
                MealRequest.request_time,
                MealRequest.notes,
                MealRequest.closed_time,
                MealType.name_en.label("meal_type_en"),
                MealType.name_ar.label("meal_type_ar"),
                func.count(MealRequestLine.id).label("total_request_lines"),
                func.sum(
                    case((MealRequestLine.is_accepted, 1), else_=0)
                ).label("accepted_request_lines"),
            )
            .select_from(MealRequest)
            .join(MealRequestStatus, MealRequest.status_id == MealRequestStatus.id)
            .join(User, MealRequest.requester_id == User.id)
            .join(MealType, MealRequest.meal_type_id == MealType.id)
            .outerjoin(
                MealRequestLine,
                (MealRequestLine.meal_request_id == MealRequest.id) &
                (MealRequestLine.is_deleted == False),  # noqa: E712
            )
            .where(
                MealRequest.id == meal_request_id,
                MealRequest.request_time.isnot(None),
                MealRequest.is_deleted == False,  # noqa: E712
            )
            .group_by(
                MealRequest.id,
                MealRequestStatus.id,
                MealRequestStatus.name_en,
                MealRequestStatus.name_ar,
                User.username,
                User.title,
                MealRequest.notes,
                MealType.name_en,
                MealType.name_ar,
                MealRequest.request_time,
                MealRequest.closed_time,
            )
            .having(func.count(MealRequestLine.id) > 0)  # Only show request if it has active lines
        )

        try:
            result = await session.execute(stmt)
            meal_request = result.first()

            if not meal_request:
                return None

            return MealRequestSummary(**meal_request._asdict())
        except Exception as e:
            raise DatabaseError(
                f"Failed to read meal request {meal_request_id}: {str(e)}"
            )

    async def get_status_counts(self, session: AsyncSession) -> dict:
        """Get counts of meal requests by status."""
        try:
            stmt = (
                select(
                    MealRequestStatus.name_en.label("status"),
                    func.count(MealRequest.id).label("count"),
                )
                .join(
                    MealRequest, MealRequest.status_id == MealRequestStatus.id
                )
                .where(
                    MealRequest.request_time.isnot(None),
                    MealRequest.is_deleted == False,  # noqa: E712
                )
                .group_by(MealRequestStatus.name_en, MealRequestStatus.name_ar)
            )

            result = await session.execute(stmt)
            rows = result.all()

            # Initialize counts
            stats = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

            # Populate counts from query results (using English names as keys)
            for row in rows:
                status_name = row.status.lower()
                count = row.count
                stats["total"] += count
                if status_name in stats:
                    stats[status_name] = count

            return stats
        except Exception as e:
            raise DatabaseError(f"Failed to get status counts: {str(e)}")

    async def get_filtered_status_counts(
        self,
        session: AsyncSession,
        requester_filter: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        department_ids: Optional[List[int]] = None,
    ) -> dict:
        """
        Get counts of meal requests by status with filters applied.

        Uses the same filter logic as read_meal_request_for_request_details_page
        but excludes status filter to show counts across all statuses for the
        filtered dataset (requester, date range, departments).

        Args:
            department_ids: If provided (non-empty), only count meal requests that have
                           at least one line in these departments. If None or empty,
                           count all meal requests (no department restriction).
        """
        from datetime import datetime

        try:
            stmt = (
                select(
                    MealRequestStatus.name_en.label("status"),
                    func.count(func.distinct(MealRequest.id)).label("count"),
                )
                .join(
                    MealRequest, MealRequest.status_id == MealRequestStatus.id
                )
                .join(User, MealRequest.requester_id == User.id)
            )

            # Apply same filters as the list query (except status)
            filters = [
                MealRequest.request_time.isnot(None),
                MealRequest.is_deleted == False,  # noqa: E712 - Exclude soft-deleted requests
            ]

            # Exclude "On Progress" status (4) from stats as well
            filters.append(MealRequestStatus.id != 4)

            # Department filter - if user has department assignments, filter by them
            if department_ids:
                stmt = stmt.outerjoin(
                    MealRequestLine,
                    MealRequestLine.meal_request_id == MealRequest.id,
                ).outerjoin(
                    Employee, MealRequestLine.employee_id == Employee.id
                )
                filters.append(Employee.department_id.in_(department_ids))

            # Requester filter - check if it's a UUID (exact match on requester_id) or a name search
            if requester_filter and requester_filter.strip():
                if UUID_PATTERN.match(requester_filter.strip()):
                    # Exact match on requester_id (for /my-requests endpoint)
                    filters.append(
                        MealRequest.requester_id == requester_filter.strip()
                    )
                else:
                    # Partial match on username (for search functionality)
                    filters.append(
                        User.username.ilike(f"%{requester_filter}%")
                    )

            # Date filters
            if from_date:
                try:
                    from_dt = datetime.fromisoformat(
                        from_date.replace("Z", "+00:00")
                    )
                    filters.append(MealRequest.request_time >= from_dt)
                except ValueError:
                    pass

            if to_date:
                try:
                    to_dt = datetime.fromisoformat(
                        to_date.replace("Z", "+00:00")
                    )
                    filters.append(MealRequest.request_time <= to_dt)
                except ValueError:
                    pass

            stmt = stmt.where(*filters).group_by(
                MealRequestStatus.name_en, MealRequestStatus.name_ar
            )

            result = await session.execute(stmt)
            rows = result.all()

            # Initialize counts
            stats = {"total": 0, "pending": 0, "approved": 0, "rejected": 0}

            # Populate counts from query results
            for row in rows:
                status_name = row.status.lower()
                count = row.count
                stats["total"] += count
                if status_name in stats:
                    stats[status_name] = count

            return stats
        except Exception as e:
            raise DatabaseError(
                f"Failed to get filtered status counts: {str(e)}"
            )

    async def set_request_time(
        self, session: AsyncSession, request_id: int
    ) -> Optional[MealRequest]:
        """Set request_time for a meal request (used during creation)."""
        try:
            meal_request = await self.get_by_id(session, request_id)
            if meal_request:
                meal_request.request_time = datetime.now()
                await session.flush()
                return meal_request
            return None
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to set request time: {str(e)}")

    async def get_pending_copy(
        self,
        session: AsyncSession,
        original_request_id: int,
        requester_id: str,
    ) -> Optional[MealRequest]:
        """
        Check if there's already a pending copy of the given original request.

        Looks for any meal request that:
        - Has original_request_id pointing to the given original
        - Is in Pending status
        - Belongs to the given requester
        - Is not deleted

        Args:
            session: Database session
            original_request_id: ID of the original request
            requester_id: UUID of the requester

        Returns:
            The existing pending copy if found, None otherwise
        """
        # Get pending status first
        pending_status = await session.execute(
            select(MealRequestStatus).where(
                func.lower(MealRequestStatus.name_en) == "pending"
            )
        )
        pending = pending_status.scalar_one_or_none()
        if not pending:
            return None

        # Check for existing pending copy
        result = await session.execute(
            select(MealRequest).where(
                MealRequest.original_request_id == original_request_id,
                MealRequest.status_id == pending.id,
                MealRequest.requester_id == requester_id,
                ~MealRequest.is_deleted,
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete_request(
        self,
        session: AsyncSession,
        request_id: int,
        user_id: str,
    ) -> MealRequest:
        """
        Soft delete a meal request with transaction locking and security validation.

        This method implements a secure soft delete with the following guarantees:
        1. Row-level locking (SELECT FOR UPDATE) to prevent race conditions
        2. Validates user owns the request
        3. Validates status is PENDING
        4. Soft deletes the request and all its lines
        5. Prevents deletion if already deleted

        Args:
            session: Database session (must be within a transaction)
            request_id: ID of the meal request to delete
            user_id: UUID of the user performing the deletion

        Returns:
            The soft-deleted MealRequest instance

        Raises:
            NotFoundError: If request doesn't exist
            AuthorizationError: If user doesn't own the request
            ValidationError: If request status is not PENDING or already deleted
            DatabaseError: If deletion fails
        """
        from core.exceptions import AuthorizationError, ValidationError

        try:
            # Step 1: Lock the row to prevent race conditions
            stmt = (
                select(MealRequest)
                .where(MealRequest.id == request_id)
                .with_for_update()  # 🔒 CRITICAL: Row-level lock
            )
            result = await session.execute(stmt)
            request = result.scalar_one_or_none()

            # Step 2: Validate request exists
            if not request:
                raise NotFoundError(entity="MealRequest", identifier=request_id)

            # Step 3: Validate ownership
            if request.requester_id != user_id:
                raise AuthorizationError(
                    "You are not authorized to delete this meal request"
                )

            # Step 4: Get PENDING status dynamically
            from api.repositories.meal_request_status_repository import MealRequestStatusRepository
            status_repo = MealRequestStatusRepository()
            pending_status = await status_repo.get_by_name_en(session, "Pending")

            if not pending_status:
                raise DatabaseError("PENDING status not found in database")

            # Step 5: Validate status is PENDING (CRITICAL SECURITY CHECK)
            if request.status_id != pending_status.id:
                # Get current status name for error message
                current_status = await session.get(MealRequestStatus, request.status_id)
                status_name = current_status.name_en if current_status else "Unknown"
                raise ValidationError(
                    f"Cannot delete meal request with status: {status_name}. "
                    "Only PENDING requests can be deleted."
                )

            # Step 6: Check if already deleted
            if request.is_deleted:
                raise ValidationError("Meal request has already been deleted")

            # Step 7: Soft delete the request
            request.is_deleted = True
            request.updated_at = datetime.now(timezone.utc)

            # Step 8: Soft delete all associated lines
            await session.execute(
                update(MealRequestLine)
                .where(MealRequestLine.meal_request_id == request_id)
                .values(
                    is_deleted=True,
                    updated_at=datetime.now(timezone.utc)
                )
            )

            await session.flush()
            return request

        except (NotFoundError, AuthorizationError, ValidationError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            await session.rollback()
            raise DatabaseError(f"Failed to soft delete meal request: {str(e)}")
