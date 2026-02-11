"""
Request router group registration.

Registers all request-related routers:
- meal_request_router
- meal_requests_router
- my_requests_router
"""

from fastapi import FastAPI

from api.routers.request.meal_request_router import router as meal_request_router
from api.routers.request.requests_router import router as requests_router
from api.routers.request.my_requests_router import router as my_requests_router


def register_request_routers(app: FastAPI) -> None:
    """
    Register all request routers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.include_router(meal_request_router)
    app.include_router(requests_router)
    app.include_router(my_requests_router)
