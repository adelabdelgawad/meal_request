"""
Setting router group registration.

Registers all setting/configuration-related routers:
- pages_router
- roles_router
- departments_router
- meal_type_setup_router
- users_router
- scheduler_router
"""

from fastapi import FastAPI

from api.routers.setting.pages_router import router as pages_router
from api.routers.setting.roles_router import router as roles_router
from api.routers.setting.departments_router import router as departments_router
from api.routers.setting.meal_type_setup_router import router as meal_type_setup_router
from api.routers.setting.users_router import router as users_router
from api.routers.setting.scheduler.scheduler_router import router as scheduler_router


def register_setting_routers(app: FastAPI) -> None:
    """
    Register all setting routers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.include_router(pages_router)
    app.include_router(roles_router)
    app.include_router(departments_router)
    app.include_router(meal_type_setup_router)
    app.include_router(users_router)
    app.include_router(scheduler_router)
