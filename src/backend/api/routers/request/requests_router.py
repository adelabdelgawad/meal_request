"""
Meal Request Endpoints - Create and manage meal requests.
"""

import logging
import os
import traceback
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select

from core.dependencies import SessionDep, CurrentUserDep, ActiveUserDep get_session
from db.model import DepartmentAssignment
from api.schemas.meal_request_schemas import (
    CopyMealRequestResponse,
    MealRequestCreateResponse,
    MealRequestStatusUpdateResponse,
)
from api.services import (
    EmailService,
    EmployeeService,
    LogMealRequestLineService,
    MealRequestService,
)
from api.services.log_meal_request_service import LogMealRequestService
from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from db.model import Employee, MealRequest, MealRequestLine
from core.config import settings
from utils.app_schemas import (
    AuditRecordResponse,
    MealRequestLineRequest,
    MealRequestLineResponse,
    MealRequestSummary,
    UpdateMealRequestLineRequest,
)
from utils.mail_sender import EmailSender
from utils.security import (
    limiter,
    require_auditor_or_admin,
    require_authenticated,
    require_ordertaker_auditor_or_admin,
    require_ordertaker_or_admin,
    require_requester_or_admin,
    require_requester_ordertaker_or_admin,
)

router = APIRouter(prefix="/request/requests", tags=["request-requests"])
logger = logging.getLogger(__name__)

# Initialize services
email_service = EmailService(session)
employee_service = EmployeeService(session)
meal_request_service = MealRequestService(session)
log_meal_request_line_service = LogMealRequestLineService(session)
log_meal_request_service = LogMealRequestService(session)


def generate_new_request_template(data: dict, file_name: str) -> str:
    """
    Generates an email template with the provided data.

    Args:
        data (dict): The data to be used in the template.
        file_name (str): The name of the template file.

    Returns:
        str: Rendered HTML content from the template.
    """
    env = Environment(loader=FileSystemLoader(os.path.abspath("templates")))
    template = env.get_template(file_name)
    return template.render(data)


def send_notification_background(
    request_id: int,
    request_lines: int,
    to_recipient: str,
    cc_recipients: Optional[List[str]] = None,
):
    """
    Background task to send notification email.

    Uses Celery when CELERY_ENABLED=True for retry support.
    Falls back to direct execution otherwise.
    """
    # Try Celery dispatch first
    if settings.celery.enabled:
        try:
            from tasks.email import send_notification_task

            send_notification_task.delay(
                request_id=request_id,
                request_lines=request_lines,
                to_recipient=to_recipient,
                cc_recipients=cc_recipients,
            )
            logger.info(f"Email task dispatched to Celery for request #{request_id}")
            return
        except ImportError as e:
            logger.warning(
                f"Celery email task not available: {e}, falling back to direct send"
            )
        except Exception as e:
            logger.warning(
                f"Failed to dispatch to Celery: {e}, falling back to direct send"
            )

    # Fallback: Direct send (original behavior)
    try:
        body_html = generate_new_request_template(
            {"request_lines": request_lines}, "request.html"
        )

        subject = f"Meal Request Submitted #{request_id} - Confirmation Pending"

        email_sender = EmailSender()
        message = email_sender.create_message(
            subject=subject,
            body=body_html,
            to_recipient=to_recipient,
            cc_recipients=cc_recipients,
        )
        message.send()
        logger.info(f"Email sent successfully to {to_recipient}")

    except Exception as e:
        logger.error(f"Failed to send email to {to_recipient}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


async def process_meal_requests_for_employees(
    maria_db_session: AsyncSession,
    request_lines: List[MealRequestLineRequest],
    meal_request_id: int,
) -> Optional[List[MealRequestLine]]:
    """
    Process meal request lines for multiple employees.

    1. Create request lines with employee and department info
    2. Optionally get shift information
    """
    created_request_lines = []

    try:
        # Create all request lines
        for line in request_lines:
            try:
                # Fetch employee to get employee_code
                employee_stmt = select(Employee).where(Employee.id == line.employee_id)
                employee_result = await maria_db_session.execute(employee_stmt)
                employee = employee_result.scalar_one_or_none()

                if not employee:
                    logger.error(
                        f"Employee {line.employee_id} not found, skipping line"
                    )
                    continue

                # Create the request line (SQLAlchemy model instance)
                # employee_code is auto-populated from employee record
                meal_request_line = MealRequestLine(
                    employee_id=line.employee_id,
                    employee_code=employee.code,  # Auto-populated from employee
                    meal_request_id=meal_request_id,
                    notes=line.notes,
                    attendance_time=None,  # Optional: can be added later
                    shift_hours=None,  # Optional: can be added later
                    is_accepted=True,  # Default to accepted on creation
                    is_deleted=False,
                )
                created_line = await meal_request_service.create_meal_request_line(
                    maria_db_session, meal_request_line
                )
                created_request_lines.append(created_line)
                logger.info(
                    f"Created meal request line ID {created_line.id} for employee {line.employee_id}"
                )

            except Exception as line_err:
                logger.error(
                    f"Failed to create request line for employee {line.employee_id}: {line_err}"
                )
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue with other lines

        logger.info(
            f"Successfully created {len(created_request_lines)} request lines out of {len(request_lines)} total"
        )
        return created_request_lines

    except Exception as e:
        logger.error(f"Error processing meal requests for employees: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return created_request_lines if created_request_lines else None


@router.get("/employees")
async def get_employees(
    session: SessionDep,
    payload: dict = Depends(require_requester_ordertaker_or_admin),
):
    """
    Retrieves active employees grouped by department.
    Requires Requester, Ordertaker, or Admin role.

    Department visibility:
    - If the user has department assignments, only employees from those departments
      (and their children) are shown
    - If the user has NO department assignments, ALL employees are shown
    """
    try:
        # Get user's expanded department IDs for visibility filtering
        user_id = payload.get("user_id") or payload.get("sub")
        department_ids = None

        if user_id:
            from api.repositories import DepartmentAssignmentRepository

            DepartmentAssignmentRepository()
            # Get department IDs from user's department assignments
            dept_ids_result = await session.execute(
                select(DepartmentAssignment.department_id)
                .where(DepartmentAssignment.user_id == user_id)
                .where(DepartmentAssignment.is_active)
                .distinct()
            )
            user_dept_ids = [row[0] for row in dept_ids_result]
            if user_dept_ids:
                department_ids = user_dept_ids
                logger.info(
                    f"User {user_id} can see departments from assignments: {department_ids}"
                )

        employees = await employee_service.get_active_employees_grouped_flat(
            session, department_ids=department_ids
        )
        return employees if employees else {}
    except Exception as e:
        logger.error(f"Error retrieving employees: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while fetching employees.",
        )


@router.post("/", response_model=MealRequestCreateResponse)
@limiter.limit("100/minute")
async def create_meal_request_endpoint(
    request: Request,
    requester_id: str,
    meal_type_id: int,
    request_lines: List[MealRequestLineRequest],
    background_tasks: BackgroundTasks,
    maria_session: SessionDep,
    payload: dict = Depends(require_requester_or_admin),
) -> MealRequestCreateResponse:
    """Endpoint to create a new meal request. Requires Requester or Admin role."""
    try:
        logger.info(
            f"Received request for requester_id {requester_id}: {len(request_lines)} lines"
        )
        # Create MealRequest model with "On Progress" status (4)
        # This allows immediate response while attendance is fetched asynchronously
        meal_request_model = MealRequest(
            requester_id=requester_id,
            meal_type_id=meal_type_id,
            status_id=4,  # On Progress status - will be updated to Pending (1) after attendance fetch
            notes="",
        )
        meal_request_record = await meal_request_service.create_meal_request(
            maria_session,
            meal_request_model,
        )

        # Create request lines immediately (without attendance_time)
        logger.info(f"Creating {len(request_lines)} request lines immediately")

        created_lines = await process_meal_requests_for_employees(
            maria_db_session=maria_session,
            request_lines=request_lines,
            meal_request_id=meal_request_record.id,
        )

        if created_lines:
            logger.info(f"Successfully created {len(created_lines)} request lines")
        else:
            logger.warning("No request lines were created")

        # Commit the transaction to ensure the meal request and lines are saved
        await maria_session.commit()

        # Dispatch Celery task to fetch attendance asynchronously
        # The task will update attendance_time for each line and change status to Pending (1)
        if settings.celery.enabled:
        try:
            from tasks.email import send_status_update_task

            send_status_update_task.delay(
                request_id=request_id,
                status=status,
                to_recipient=to_recipient,
                cc_recipients=cc_recipients,
            )
            logger.info(f"Email task dispatched to Celery for request #{request_id}")
            return
        except ImportError as e:
            logger.warning(
                f"Celery email task not available: {e}, falling back to direct send"
            )
        except Exception as e:
            logger.warning(
                f"Failed to dispatch to Celery: {e}, falling back to direct send"
            )
                logger.info(
                    f"Dispatched attendance fetch task for meal request {meal_request_record.id}"
                )
            except ImportError as e:
                logger.warning(
                    f"Celery attendance task not available: {e}, status will remain On Progress"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to dispatch attendance fetch task: {e}, status will remain On Progress"
                )
        else:
            logger.info("Celery disabled, attendance fetch task not dispatched")

        # Log meal request creation
        user_id = payload.get("user_id") or payload.get("sub")
        await log_meal_request_service.log_meal_request(
            session=maria_session,
            user_id=user_id,
            meal_request_id=meal_request_record.id,
            action="create",
            is_successful=True,
            result={
                "meal_type_id": meal_request_record.meal_type_id,
                "employee_count": len(created_lines) if created_lines else 0,
                "status_id": meal_request_record.status_id,
            },
        )

        return MealRequestCreateResponse(
            message="Request Added Successfully",
            meal_request_id=meal_request_record.id,
        )

    except Exception as e:
        logger.error(f"General error in create_meal_request_endpoint: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/stats")
async def get_meal_request_stats(
    requester: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    session: SessionDep,
    payload: dict = Depends(require_ordertaker_auditor_or_admin),
):
    """Get statistics about meal requests (counts by status) with optional filtering. Requires Ordertaker, Auditor, or Admin role."""
    logger.info(
        f"Fetching meal request statistics with filters: requester={requester}, from_date={from_date}, to_date={to_date}"
    )
    try:
        # If no filters provided, use the simple stats endpoint
        if not requester and not from_date and not to_date:
            stats = await meal_request_service.get_meal_request_stats(session)
        else:
            # Use filtered stats endpoint when filters are provided
            stats = await meal_request_service.get_filtered_meal_request_stats(
                session,
                requester_filter=requester,
                from_date=from_date,
                to_date=to_date,
            )
        logger.info(f"Statistics: {stats}")
        return stats
    except Exception as err:
        logger.error(f"Error fetching meal request stats: {err}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching statistics.",
        )


@router.get("/all")
async def get_meal_requests(
    request: Request,
    status_id: Optional[int] = None,
    requester: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    session: SessionDep,
    token_data: dict = Depends(require_ordertaker_auditor_or_admin),
):
    """
    Retrieve meal requests from the database with optional filters and pagination.
    Requires Ordertaker, Auditor, or Admin role.

    Returns a unified response with items, pagination metadata, and stats.
    Stats are computed using the same filters (requester, date range) but exclude
    status filter to show counts across all statuses for the filtered dataset.

    NOTE: This endpoint does NOT apply department filtering.
    All users with proper roles can see all meal requests.
    Department filtering only applies to the /meal-request endpoint.
    """
    logger.info(
        f"Attempting to read meal requests with filters: status_id={status_id}, requester={requester}, from_date={from_date}, to_date={to_date}, page={page}, page_size={page_size}"
    )
    try:
        # /requests endpoint does NOT apply department filtering
        # Department filtering only applies to /meal-request endpoint
        # All users with proper roles can see all meal requests here

        # Get paginated results and total count (no department filtering)
        (
            meal_requests,
            total_count,
        ) = await meal_request_service.get_meal_requests_for_details_page(
            session,
            status_id=status_id,
            requester_filter=requester,
            from_date=from_date,
            to_date=to_date,
            department_ids=None,  # No department filtering on /requests
            page=page,
            page_size=page_size,
        )

        # Get stats with same filters (no department filtering)
        stats = await meal_request_service.get_filtered_meal_request_stats(
            session,
            requester_filter=requester,
            from_date=from_date,
            to_date=to_date,
            department_ids=None,  # No department filtering on /requests
        )

        if not meal_requests:
            logger.info("No meal requests found")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "stats": stats,
            }

        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        logger.info(
            f"Found {len(meal_requests)} meal requests (page {page} of {total_pages}, total: {total_count})"
        )

        return {
            "items": meal_requests,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "stats": stats,
        }

    except HTTPException as http_exc:
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise http_exc

    except Exception as err:
        logger.error(f"Error reading meal requests: {err}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while reading meal requests.",
        )


@router.get("/lines")
async def get_meal_request_line(
    request_id: Optional[int] = None,
    session: SessionDep,
    payload: dict = Depends(require_ordertaker_auditor_or_admin),
) -> List[MealRequestLineResponse]:
    """Get meal request lines for a specific request. Requires Ordertaker, Auditor, or Admin role."""
    logger.info("Attempting to read meal request lines")
    try:
        meal_request_line = (
            await meal_request_service.get_meal_request_lines_for_request(
                session, request_id
            )
        )
        if not meal_request_line:
            logger.info(f"No meal request lines found for request_id={request_id}")
            return []  # Return empty array instead of 404
        logger.info(f"Found {len(meal_request_line)} meal request lines")
        return meal_request_line

    except HTTPException as http_exc:
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise http_exc

    except Exception as err:
        logger.error(f"Error reading meal request lines: {err}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while reading meal request lines.",
        )


@router.put("/lines/{line_id}")
@limiter.limit("100/minute")
async def update_meal_request_line_status_endpoint(
    request: Request,
    line_id: int,
    update_request: UpdateMealRequestLineRequest,
    session: SessionDep,
    payload: dict = Depends(require_ordertaker_or_admin),
):
    """Update meal request line status and notes. Requires Ordertaker or Admin role."""
    try:
        # Fetch the line BEFORE updating to capture old values
        from api.repositories.meal_request_line_repository import (
            MealRequestLineRepository,
        )

        line_repo = MealRequestLineRepository()
        existing_line = await line_repo.get_by_id(
            session, update_request.meal_request_line_id
        )

        if not existing_line:
            logger.info(
                f"No meal request line by ID: {update_request.meal_request_line_id} found to update"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No meal request line by ID: {update_request.meal_request_line_id} found to update.",
            )

        # Store old values before updating
        old_accepted = existing_line.is_accepted
        old_notes = existing_line.notes or ""
        meal_request_id = existing_line.meal_request_id

        # Now perform the update
        meal_request_line = await meal_request_service.update_meal_request_line(
            session,
            update_request.meal_request_line_id,
            update_request.accepted,
            update_request.notes,
        )

        # Log with correct old vs new values
        await log_meal_request_service.log_meal_request(
            session,
            user_id=update_request.user_id,
            action="update_line",
            is_successful=True,
            meal_request_id=meal_request_id,
            old_value={
                "accepted": old_accepted,
                "notes": old_notes,
            },
            new_value={
                "accepted": update_request.accepted,
                "notes": update_request.notes or "",
            },
            result={
                "meal_request_line_id": meal_request_line.id,
                "action": "update_notes_or_acceptance",
            },
        )
        logger.info(
            f"Meal request line: {update_request.meal_request_line_id} status and notes updated successfully"
        )
        # Return simple response
        return {
            "message": "Meal request line updated successfully",
            "id": meal_request_line.id,
            "is_accepted": meal_request_line.is_accepted,
        }

    except HTTPException as http_exc:
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise http_exc

    except Exception as err:
        logger.error(f"Error updating meal request line: {err}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating meal request line.",
        )


@router.put("/{meal_request_id}/status", response_model=MealRequestSummary)
@limiter.limit("100/minute")
async def update_meal_request_status_endpoint(
    request: Request,
    meal_request_id: int,
    status_id: int,
    user_id: str,
    background_tasks: BackgroundTasks,
    expected_status_id: Optional[int] = None,
    session: SessionDep,
    payload: dict = Depends(require_ordertaker_or_admin),
) -> MealRequestSummary:
    """
    Update the status of a meal request. Requires Ordertaker or Admin role.

    Supports optimistic locking via expected_status_id parameter.
    If provided, the update will only proceed if the current status matches
    the expected status. This prevents race conditions when multiple users
    try to update the same request.
    """
    try:
        logger.info(
            f"Updating meal request {meal_request_id} with status {status_id} for user {user_id}"
        )

        # Check for concurrency conflict if expected_status_id is provided
        current_request = None
        old_status_id = None
        if expected_status_id is not None:
            current_request = await meal_request_service.get_request(
                session, meal_request_id
            )
            if current_request:
                old_status_id = current_request.status_id
                if current_request.status_id != expected_status_id:
                    logger.warning(
                        f"Concurrency conflict: meal request {meal_request_id} has status {current_request.status_id}, "
                        f"expected {expected_status_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "code": "STATUS_ALREADY_CHANGED",
                            "message": "This request has already been updated by another user. Please refresh to see the latest status.",
                            "current_status_id": current_request.status_id,
                            "expected_status_id": expected_status_id,
                        },
                    )
        else:
            # Get current request to capture old status for audit
            current_request = await meal_request_service.get_request(
                session, meal_request_id
            )
            if current_request:
                old_status_id = current_request.status_id

        meal_request = await meal_request_service.update_meal_request_status(
            session, meal_request_id, status_id, user_id
        )

        if not meal_request:
            logger.info(f"No meal request found with ID {meal_request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No meal request found with ID {meal_request_id}.",
            )

        logger.info(f"Successfully updated meal request {meal_request_id}")

        # Log meal request status update
        acting_user_id = payload.get("user_id") or payload.get("sub")
        action_type = (
            "approve"
            if status_id == 2
            else "reject"
            if status_id == 3
            else "update_status"
        )
        await log_meal_request_service.log_meal_request(
            session=session,
            user_id=acting_user_id,
            meal_request_id=meal_request_id,
            action=action_type,
            is_successful=True,
            old_value=(
                {"status_id": old_status_id} if old_status_id is not None else None
            ),
            new_value={"status_id": status_id},
            result={
                "action": action_type,
                "updated_by": user_id,
            },
        )

        # Business logic for request line acceptance
        if status_id == 2:  # Approved status
            # Set all request lines to accepted (user can manually override individual lines)
            await meal_request_service.update_meal_order_line_status_by_meal_order(
                session, meal_request.id, True
            )
            logger.info(f"Set all lines to accepted for meal request {meal_request_id}")
        elif status_id == 3:  # Rejected status
            # Force all request lines to not accepted
            await meal_request_service.update_meal_order_line_status_by_meal_order(
                session, meal_request.id, False
            )
            logger.info(f"Set all lines to rejected for meal request {meal_request_id}")

        await meal_request_service.get_meal_request_lines_for_request(
            session, meal_request.id
        )

        # Fetch and return the full updated meal request with aggregated data
        updated_request_summary = (
            await meal_request_service.get_single_meal_request_summary(
                session, meal_request_id
            )
        )

        if not updated_request_summary:
            logger.error(
                f"Failed to fetch updated meal request summary for ID {meal_request_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch updated request data",
            )

        return updated_request_summary

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating meal request.",
        )


# Additional endpoints matching frontend expectations
@router.post("/create-meal-request")
@limiter.limit("100/minute")
async def create_meal_request_frontend(
    request: Request,
    requester_id: str,
    meal_type_id: int,
    request_lines: List[MealRequestLineRequest],
    background_tasks: BackgroundTasks,
    maria_session: SessionDep,
    payload: dict = Depends(require_requester_or_admin),
):
    """
    Create a new meal request (frontend-compatible endpoint).
    This is an alias for POST /requests/ to match frontend expectations.
    Requires Requester or Admin role.
    """
    return await create_meal_request_endpoint(
        request,
        requester_id,
        meal_type_id,
        request_lines,
        background_tasks,
        maria_session,
        payload,
    )


@router.get("/request-lines")
async def get_request_lines_frontend(
    request_id: Optional[int] = None,
    session: SessionDep,
    payload: dict = Depends(require_ordertaker_auditor_or_admin),
) -> List[MealRequestLineResponse]:
    """
    Get meal request lines (frontend-compatible endpoint).
    This is an alias for GET /requests/lines to match frontend expectations.
    Requires Ordertaker, Auditor, or Admin role.
    """
    return await get_meal_request_line(request_id, session, payload)


@router.get("/audit-request", response_model=Optional[List[AuditRecordResponse]])
async def get_audit_request(
    start_time: datetime,
    end_time: datetime,
    session: SessionDep,
    payload: dict = Depends(require_auditor_or_admin),
) -> Optional[List[AuditRecordResponse]]:
    """
    Get detailed audit report for meal requests within a time range.
    Requires Auditor or Admin role.

    Args:
        start_time: Start time for audit period (ISO string)
        end_time: End time for audit period (ISO string)
        session: Database session

    Returns:
        List of audit records with employee and attendance details
    """
    try:
        logger.info(f"Fetching audit records from {start_time} to {end_time}")

        # Get closed and accepted meal request lines with all joined data
        audit_records = (
            await meal_request_service.get_closed_accepted_requests_for_audit(
                session, start_time, end_time
            )
        )

        if not audit_records:
            logger.info("No audit records found for the given time range")
            return []

        logger.info(f"Found {len(audit_records)} audit records")
        return audit_records

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc

    except Exception as err:
        logger.error(f"Unexpected error in audit endpoint: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching audit records.",
        )


@router.put("/update-meal-request", response_model=MealRequestStatusUpdateResponse)
@limiter.limit("100/minute")
async def update_meal_request_frontend(
    request: Request,
    meal_request_id: int,
    status_id: int,
    account_id: str,
    session: SessionDep,
    payload: dict = Depends(require_ordertaker_or_admin),
) -> MealRequestStatusUpdateResponse:
    """
    Update meal request status (frontend-compatible endpoint).
    Requires Ordertaker or Admin role.

    Args:
        meal_request_id: ID of the meal request to update
        status_id: New status ID (2=Approved, 3=Rejected)
        account_id: ID of the user making the update
        session: Database session

    Returns:
        Success message with updated meal request data
    """
    try:
        logger.info(
            f"Updating meal request {meal_request_id} to status {status_id} by account {account_id}"
        )

        meal_request = await meal_request_service.update_meal_request_status(
            session, meal_request_id, status_id, account_id
        )

        if not meal_request:
            logger.info(f"No meal request found with ID {meal_request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No meal request found with ID {meal_request_id}.",
            )

        logger.info(f"Successfully updated meal request {meal_request_id}")

        # If rejecting (status_id=3), update all lines to not accepted
        if status_id == 3:
            await meal_request_service.update_meal_order_line_status_by_meal_order(
                session, meal_request.id, False
            )

        return MealRequestStatusUpdateResponse(
            message="Meal request updated successfully",
            meal_request_id=meal_request.id,
            status_id=meal_request.status_id,
            closed_by_id=(
                str(meal_request.closed_by_id) if meal_request.closed_by_id else None
            ),
            closed_time=meal_request.closed_time,
        )

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating meal request.",
        )


@router.get("/status-options")
async def get_status_options(
    active_only: bool = True,
    session: SessionDep,
    payload: dict = Depends(require_authenticated),
):
    """
    Get meal request status options. Requires authentication.

    Args:
        active_only: If True, return only active statuses (default: True)
        session: Database session

    Returns:
        List of status options with id, name_en, name_ar, is_active
    """
    try:
        from api.repositories import MealRequestStatusRepository

        status_repo = MealRequestStatusRepository()

        if active_only:
            statuses = await status_repo.get_active_statuses(session)
        else:
            statuses, _ = await status_repo.list(session, page=1, per_page=100)

        return [
            {
                "id": s.id,
                "name_en": s.name_en,
                "name_ar": s.name_ar,
                "is_active": s.is_active,
            }
            for s in statuses
        ]

    except Exception as err:
        logger.error(f"Error fetching status options: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch status options",
        )


@router.get("/my")
async def get_my_meal_requests(
    request: Request,
    status_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    session: SessionDep,
    token_data: dict = Depends(require_requester_or_admin),
):
    """
    Retrieve meal requests created by the current user (requester).
    Requires Requester or Admin role.

    This endpoint returns only the requests where the current user is the requester,
    allowing users to monitor their own submitted requests.

    Returns a unified response with items, pagination metadata, and stats.
    """
    logger.info(
        f"Attempting to read user's own meal requests with filters: status_id={status_id}, from_date={from_date}, to_date={to_date}, page={page}, page_size={page_size}"
    )
    try:
        # Get current user's ID from JWT token
        user_id = token_data.get("user_id") or token_data.get("sub")

        if not user_id:
            logger.error("No user_id found in token data")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User identification not found in token",
            )

        logger.info(f"Fetching requests for requester: {user_id}")

        # Get paginated results filtered by requester_id = current user
        (
            meal_requests,
            total_count,
        ) = await meal_request_service.get_meal_requests_for_details_page(
            session,
            status_id=status_id,
            requester_filter=user_id,  # Filter by current user's ID
            from_date=from_date,
            to_date=to_date,
            department_ids=None,  # No department filtering for user's own requests
            page=page,
            page_size=page_size,
        )

        # Get stats for the user's own requests
        stats = await meal_request_service.get_filtered_meal_request_stats(
            session,
            requester_filter=user_id,
            from_date=from_date,
            to_date=to_date,
            department_ids=None,
        )

        if not meal_requests:
            logger.info(f"No meal requests found for user {user_id}")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "stats": stats,
            }

        total_pages = (total_count + page_size - 1) // page_size
        logger.info(
            f"Found {len(meal_requests)} meal requests for user {user_id} (page {page} of {total_pages}, total: {total_count})"
        )

        return {
            "items": meal_requests,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "stats": stats,
        }

    except HTTPException as http_exc:
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise http_exc

    except Exception as err:
        logger.error(f"Error reading user's meal requests: {err}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while reading your meal requests.",
        )


@router.post("/{request_id}/copy", response_model=CopyMealRequestResponse)
@limiter.limit("20/minute")
async def copy_meal_request_endpoint(
    request: Request,
    request_id: int,
    session: SessionDep,
    token_data: dict = Depends(require_requester_or_admin),
) -> CopyMealRequestResponse:
    """
    Copy an existing meal request with all its lines.
    Requires Requester or Admin role.

    Creates a new meal request with:
    - Same meal type as the original
    - Same employee lines (employee_id, employee_code, notes)
    - Fresh Pending status
    - Current timestamp as request_time
    - Reset is_accepted to True for all lines

    User can only copy their own requests that are not in Pending status.
    """
    try:
        user_id = token_data.get("user_id") or token_data.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User identification not found in token",
            )

        logger.info(f"User {user_id} copying meal request {request_id}")

        new_request, lines_copied = await meal_request_service.copy_request(
            session=session,
            source_request_id=request_id,
            requester_id=user_id,
        )

        logger.info(
            f"Successfully copied request {request_id} to {new_request.id} "
            f"with {lines_copied} lines"
        )

        # Log meal request copy operation
        await log_meal_request_service.log_meal_request(
            session=session,
            user_id=user_id,
            meal_request_id=new_request.id,
            action="copy",
            is_successful=True,
            result={
                "copied_from_id": request_id,
                "lines_copied": lines_copied,
                "meal_type_id": new_request.meal_type_id,
                "status_id": new_request.status_id,
            },
        )

        return CopyMealRequestResponse(
            message="Request copied successfully",
            original_request_id=request_id,
            new_meal_request_id=new_request.id,
            lines_copied=lines_copied,
            meal_type_id=new_request.meal_type_id,
        )

    except NotFoundError as e:
        logger.warning(f"Request not found: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except AuthorizationError as e:
        logger.warning(f"Authorization failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )
    except ValidationError as e:
        logger.warning(f"Validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error copying meal request: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while copying meal request.",
        )


# =====================================================================
# Soft Delete Endpoints - Secure deletion with transaction locking
# =====================================================================


@router.delete("/{request_id}/soft-delete")
@limiter.limit("10/minute")
async def soft_delete_meal_request(
    request_id: int,
    request: Request,
    session: SessionDep,
    current_user: dict = Depends(require_authenticated),
    payload: dict = Depends(require_requester_or_admin),
):
    """
    Soft delete a PENDING meal request.

    This endpoint implements secure soft deletion with the following guarantees:
    - Only the requester (or admin) can delete their own requests
    - Only PENDING requests can be deleted
    - Uses database transaction with row locking to prevent race conditions
    - All associated meal request lines are also soft deleted
    - Comprehensive audit logging

    Security Rules:
    - Row-level locking (SELECT FOR UPDATE) prevents race conditions
    - If request status changes during deletion, operation is blocked
    - Admin users can delete any PENDING request

    Args:
        request_id: ID of the meal request to delete
        request: FastAPI Request object
        session: Database session
        current_user: Authenticated user payload

    Returns:
        200: Successfully deleted with audit details
        400: Request status is not PENDING or already deleted
        403: Not authorized (not your request)
        404: Request not found
        500: Internal server error

    Example Response:
        {
            "success": true,
            "message": "Meal request deleted successfully",
            "requestId": 123,
            "linesDeleted": 5
        }
    """
    user_id = current_user["user_id"]

    logger.info(
        f"Soft delete request initiated: request_id={request_id}, user_id={user_id}"
    )

    try:
        async with session.begin():
            from api.repositories.meal_request_repository import MealRequestRepository

            repo = MealRequestRepository()

            # Count lines before deletion for audit
            lines_result = await session.execute(
                select(MealRequestLine).where(
                    MealRequestLine.meal_request_id == request_id,
                    MealRequestLine.is_deleted == False,  # noqa: E712
                )
            )
            lines_count = len(lines_result.scalars().all())

            # Perform soft delete with security validation
            deleted_request = await repo.soft_delete_request(
                session=session,
                request_id=request_id,
                user_id=user_id,
            )

            # Create audit log
            await log_meal_request_service.log_meal_request(
                session=session,
                user_id=user_id,
                meal_request_id=request_id,
                action="SOFT_DELETE_REQUEST",
                is_successful=True,
                old_value={
                    "status_id": deleted_request.status_id,
                    "lines_count": lines_count,
                    "requester_id": str(deleted_request.requester_id),
                },
                new_value={
                    "is_deleted": True,
                    "deleted_at": datetime.now().isoformat(),
                },
                result={
                    "lines_deleted": lines_count,
                    "success": True,
                },
            )

            await session.commit()

        logger.info(
            f"Meal request soft deleted successfully: request_id={request_id}, "
            f"lines_deleted={lines_count}"
        )

        return {
            "success": True,
            "message": "Meal request deleted successfully",
            "requestId": request_id,
            "linesDeleted": lines_count,
        }

    except AuthorizationError as e:
        logger.warning(
            f"Authorization failed for soft delete: request_id={request_id}, "
            f"user_id={user_id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except NotFoundError as e:
        logger.warning(f"Request not found for soft delete: request_id={request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            f"Validation failed for soft delete: request_id={request_id}, "
            f"error={str(e)}"
        )
        # Log failed attempt to audit
        try:
            async with session.begin():
                await log_meal_request_service.log_meal_request(
                    session=session,
                    user_id=user_id,
                    meal_request_id=request_id,
                    action="SOFT_DELETE_REQUEST_FAILED",
                    is_successful=False,
                    old_value=None,
                    new_value=None,
                    result={"error": str(e)},
                )
                await session.commit()
        except Exception as log_error:
            logger.error(f"Failed to log deletion failure: {log_error}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error soft deleting meal request: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting meal request.",
        )


@router.delete("/{request_id}/lines/{line_id}/soft-delete")
@limiter.limit("10/minute")
async def soft_delete_meal_request_line(
    request_id: int,
    line_id: int,
    request: Request,
    session: SessionDep,
    current_user: dict = Depends(require_authenticated),
    payload: dict = Depends(require_requester_or_admin),
):
    """
    Soft delete a meal request line from a PENDING request.

    This endpoint implements secure line deletion with the following guarantees:
    - Only the requester (or admin) can delete lines from their requests
    - Parent request must be PENDING
    - Validates line belongs to the specified request
    - Uses database transaction with row locking
    - Comprehensive audit logging

    Security Rules:
    - Locks parent MealRequest to validate status
    - If parent request status changes during deletion, operation is blocked
    - Admin users can delete any line from PENDING requests

    Args:
        request_id: ID of the parent meal request
        line_id: ID of the line to delete
        request: FastAPI Request object
        session: Database session
        current_user: Authenticated user payload

    Returns:
        200: Successfully deleted with audit details
        400: Parent request status is not PENDING or line already deleted
        403: Not authorized
        404: Line or request not found
        500: Internal server error

    Example Response:
        {
            "success": true,
            "message": "Meal request line deleted successfully",
            "requestId": 123,
            "lineId": 456
        }
    """
    user_id = current_user["user_id"]

    logger.info(
        f"Soft delete line initiated: request_id={request_id}, "
        f"line_id={line_id}, user_id={user_id}"
    )

    try:
        async with session.begin():
            from api.repositories.meal_request_line_repository import (
                MealRequestLineRepository,
            )

            repo = MealRequestLineRepository()

            # Perform soft delete with security validation
            deleted_line = await repo.soft_delete_line(
                session=session,
                line_id=line_id,
                request_id=request_id,
                user_id=user_id,
            )

            # Create audit log
            await log_meal_request_service.log_meal_request(
                session=session,
                user_id=user_id,
                meal_request_id=request_id,
                action="SOFT_DELETE_REQUEST_LINE",
                is_successful=True,
                old_value={
                    "line_id": line_id,
                    "employee_id": deleted_line.employee_id,
                    "employee_code": deleted_line.employee_code,
                },
                new_value={
                    "is_deleted": True,
                    "deleted_at": datetime.now().isoformat(),
                },
                result={
                    "success": True,
                    "line_id": line_id,
                },
            )

            await session.commit()

        logger.info(
            f"Meal request line soft deleted successfully: "
            f"request_id={request_id}, line_id={line_id}"
        )

        return {
            "success": True,
            "message": "Meal request line deleted successfully",
            "requestId": request_id,
            "lineId": line_id,
        }

    except AuthorizationError as e:
        logger.warning(
            f"Authorization failed for soft delete line: request_id={request_id}, "
            f"line_id={line_id}, user_id={user_id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except NotFoundError as e:
        logger.warning(
            f"Line or request not found for soft delete: "
            f"request_id={request_id}, line_id={line_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValidationError as e:
        logger.warning(
            f"Validation failed for soft delete line: request_id={request_id}, "
            f"line_id={line_id}, error={str(e)}"
        )
        # Log failed attempt to audit
        try:
            async with session.begin():
                await log_meal_request_service.log_meal_request(
                    session=session,
                    user_id=user_id,
                    meal_request_id=request_id,
                    action="SOFT_DELETE_REQUEST_LINE_FAILED",
                    is_successful=False,
                    old_value={"line_id": line_id},
                    new_value=None,
                    result={"error": str(e)},
                )
                await session.commit()
        except Exception as log_error:
            logger.error(f"Failed to log line deletion failure: {log_error}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Error soft deleting meal request line: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting meal request line.",
        )
