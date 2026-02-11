"""
Auth router group registration.

Registers all authentication-related routers:
- auth_router
- login_router
- internal_auth_router
- me_router
"""

from fastapi import FastAPI

from api.routers.auth.auth_router import router as auth_router
from api.routers.auth.login_router import router as login_router
from api.routers.auth.internal_auth_router import router as internal_auth_router
from api.routers.auth.me_router import router as me_router


def register_auth_routers(app: FastAPI) -> None:
    """
    Register all auth routers with FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.include_router(auth_router)
    app.include_router(login_router)
    app.include_router(internal_auth_router)
    app.include_router(me_router)
