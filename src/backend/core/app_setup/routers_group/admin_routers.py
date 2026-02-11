"""
Admin router group registration.

Registers all admin/configuration routers:
- admin_router
"""

from fastapi import FastAPI

from api.routers.admin.admin_router import router as admin_router


def register_admin_routers(app: FastAPI) -> None:
    """
    Register all admin routers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.include_router(admin_router)
