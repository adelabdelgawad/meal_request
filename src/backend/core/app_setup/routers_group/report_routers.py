"""
Report router group registration.

Registers all report/audit-related routers:
- analysis_router
- audit_router
- reporting_router
"""

from fastapi import FastAPI

from api.routers.report.analysis_router import router as analysis_router
from api.routers.report.audit_router import router as audit_router
from api.routers.report.reporting_router import router as reporting_router


def register_report_routers(app: FastAPI) -> None:
    """
    Register all report routers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.include_router(analysis_router)
    app.include_router(audit_router)
    app.include_router(reporting_router)
