"""
Request Analysis Endpoints - Analyze meal request data.
"""

import logging
import traceback
from datetime import datetime
from typing import List, Optional

from api.deps import get_session
from api.services import MealRequestService
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from utils.app_schemas import RequestDataResponse
from utils.security import require_ordertaker_auditor_or_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Initialize services
meal_request_service = MealRequestService()


@router.get("/closed-requests", response_model=List[RequestDataResponse] | None)
async def get_requests_data(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_ordertaker_auditor_or_admin),
):
    """Get analysis of closed requests with acceptance status. Requires Ordertaker, Auditor, or Admin role."""
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
            detail="Internal server error while fetching analysis data.",
        )


# Frontend-compatible endpoint for request analysis
@router.get("/request-analysis", response_model=List[RequestDataResponse] | None)
async def get_request_analysis(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
    payload: dict = Depends(require_ordertaker_auditor_or_admin),
):
    """Frontend-compatible endpoint for request analysis. Requires Ordertaker, Auditor, or Admin role."""
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
