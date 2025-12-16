"""
Analytics Endpoints - Frontend-compatible analytics data.
"""

import logging
import traceback
from datetime import datetime
from typing import List, Optional

from api.deps import get_session
from api.services import MealRequestService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from utils.app_schemas import RequestDataResponse
from utils.security import (require_auditor_or_admin,
                            require_ordertaker_auditor_or_admin)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Initialize services
meal_request_service = MealRequestService()


@router.get("")
async def get_analytics_data(
    start_time: datetime = Query(...,
                                 description="Start time for analytics period"),
    end_time: datetime = Query(...,
                               description="End time for analytics period"),
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_auditor_or_admin),
):
    """
    Frontend-compatible analytics endpoint.
    Requires Auditor or Admin role.
    """
    try:
        audit_records = await meal_request_service.get_closed_accepted_requests_for_audit(
            session, start_time, end_time
        )
        # Convert to dict for JSON serialization with camelCase
        data = [record.model_dump(by_alias=True) for record in audit_records] if audit_records else []
        return JSONResponse(content={"ok": True, "data": data})

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"ok": False, "error": http_exc.detail}
        )

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "ok": False, "error": "Internal server error while generating analytics data."}
        )


@router.get("/request-analysis", response_model=List[RequestDataResponse] | None)
async def get_request_analysis_data(
    start_time: Optional[datetime] = Query(
        None, description="Start time for analysis period"),
    end_time: Optional[datetime] = Query(
        None, description="End time for analysis period"),
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_ordertaker_auditor_or_admin),
):
    """
    Frontend-compatible request analysis endpoint.
    Requires Ordertaker, Auditor, or Admin role.
    """
    try:
        closed_requests = await meal_request_service.get_closed_requests_with_accept_status(
            session, start_time=start_time, end_time=end_time
        )

        return closed_requests if closed_requests else []

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        raise http_exc

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching request analysis data.",
        )


@router.get("/audit")
async def get_audit_data(
    start_time: datetime = Query(...,
                                 description="Start time for audit period"),
    end_time: datetime = Query(..., description="End time for audit period"),
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_auditor_or_admin),
):
    """
    Frontend-compatible audit endpoint.
    Requires Auditor or Admin role.
    """
    try:
        audit_records = await meal_request_service.get_closed_accepted_requests_for_audit(
            session, start_time, end_time
        )
        # Convert to dict for JSON serialization with camelCase
        data = [record.model_dump(by_alias=True) for record in audit_records] if audit_records else []
        return JSONResponse(content={"ok": True, "data": data})

    except HTTPException as http_exc:
        logger.error(f"HTTP error occurred: {http_exc.detail}")
        return JSONResponse(
            status_code=http_exc.status_code,
            content={"ok": False, "error": http_exc.detail}
        )

    except Exception as err:
        logger.error(f"Unexpected error: {err}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "ok": False, "error": "Internal server error while generating audit data."}
        )
