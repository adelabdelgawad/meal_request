import logging

from fastapi import APIRouter

# Import grouped router registration modules
from core.app_setup.routers_group.auth_routers import (
    register_auth_routers,
)
from core.app_setup.routers_group.setting_routers import (
    register_setting_routers,
)
from core.app_setup.routers_group.request_routers import (
    register_request_routers,
)
from core.app_setup.routers_group.report_routers import (
    register_report_routers,
)
from core.app_setup.routers_group.admin_routers import (
    register_admin_routers,
)

logger = logging.getLogger(__name__)


def register_all_routers(app: APIRouter) -> None:
    """
    Register all API routers with the FastAPI application.

    Iterates through each router group and calls their registration function.

    Args:
        app (APIRouter): FastAPI router instance

    Raises:
        Exception: If router registration fails

    Example:
        register_all_routers(app)
    """
    try:
        logger.info("Starting router registration")

        # Register all router groups
        register_auth_routers(app)
        register_setting_routers(app)
        register_request_routers(app)
        register_report_routers(app)
        register_admin_routers(app)

        logger.info("Successfully registered all routers")

    except Exception as e:
        logger.error(f"Router registration failed: {e}", exc_info=True)
        raise
