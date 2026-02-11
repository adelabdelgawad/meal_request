"""API Routers - Main router initialization."""

from fastapi import APIRouter

# Import all routers from subdirectories with full paths
from api.routers.report.analysis_router import router as analysis_router
from api.routers.report.audit_router import router as audit_router
from api.routers.report.reporting_router import router as reporting_router

from api.routers.request.requests_router import router as requests_router
from api.routers.request.my_requests_router import router as my_requests_router
from api.routers.request.meal_request_router import router as meal_request_router

from api.routers.setting.meal_type_setup_router import router as meal_type_setup_router
from api.routers.setting.departments_router import router as departments_router
from api.routers.setting.users_router import router as users_router
from api.routers.setting.roles_router import router as roles_router
from api.routers.setting.pages_router import router as pages_router
from api.routers.setting.scheduler.scheduler_router import router as scheduler_router

from api.routers.admin.admin_router import router as admin_router

from api.routers.auth.auth_router import router as auth_router
from api.routers.auth.login_router import router as login_router
from api.routers.auth.me_router import router as me_router
from api.routers.auth.internal_auth_router import router as internal_auth_router

# Legacy v1 routers (integrated into unified router structure)
from api.v1.navigation import router as navigation_router
from api.v1.domain_users import router as domain_users_router
from api.v1.hris import router as hris_router
from api.analytics import router as analytics_v1_router

# Create main router and include all sub-routers
main_router = APIRouter()

# Include all routers
main_router.include_router(analysis_router)
main_router.include_router(audit_router)
main_router.include_router(reporting_router)

main_router.include_router(requests_router)
main_router.include_router(my_requests_router)
main_router.include_router(meal_request_router)

main_router.include_router(meal_type_setup_router)
main_router.include_router(departments_router)
main_router.include_router(users_router)
main_router.include_router(roles_router)
main_router.include_router(pages_router)
main_router.include_router(scheduler_router)

main_router.include_router(admin_router)

main_router.include_router(auth_router)
main_router.include_router(login_router)
main_router.include_router(me_router)
main_router.include_router(internal_auth_router)

# Legacy v1 routers
main_router.include_router(navigation_router)
main_router.include_router(domain_users_router)
main_router.include_router(hris_router)

# Analytics router (separate prefix for frontend compatibility)
# Mounted at /api/v1/analytics (was previously at /api/analytics)
analytics_router_legacy = analytics_v1_router

__all__ = [
    "main_router",
    "analytics_router_legacy",
    "analysis_router",
    "audit_router",
    "reporting_router",
    "requests_router",
    "my_requests_router",
    "meal_request_router",
    "meal_type_setup_router",
    "departments_router",
    "users_router",
    "roles_router",
    "pages_router",
    "scheduler_router",
    "admin_router",
    "auth_router",
    "login_router",
    "me_router",
    "internal_auth_router",
    "navigation_router",
    "domain_users_router",
    "hris_router",
]
