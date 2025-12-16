"""
API Services - Business logic layer for all entities.

One service module per entity following clean architecture.
"""

# Auth Domain
from api.services.internal_token_service import InternalTokenService
from api.services.revoked_token_service import RevokedTokenService
from api.services.role_service import RoleService
from api.services.security_user_service import SecurityUserService
from api.services.user_service import UserService

# Meal Request Domain
from api.services.meal_request_service import MealRequestService
from api.services.meal_request_status_service import MealRequestStatusService
from api.services.meal_type_service import MealTypeService

# Organization Domain
from api.services.department_assignment_service import (
    DepartmentAssignmentService,
)
from api.services.department_service import DepartmentService
from api.services.employee_service import EmployeeService

# External Systems Domain
from api.services.hris_service import HRISService
from api.services.attendance_sync_service import AttendanceSyncService

# Config Domain
from api.services.email_role_service import EmailRoleService
from api.services.email_service import EmailService
from api.services.page_permission_service import PagePermissionService
from api.services.page_service import PageService

# Audit Domain
from api.services.log_authentication_service import LogAuthenticationService
from api.services.log_meal_request_line_service import (
    LogMealRequestLineService,
)
from api.services.log_meal_request_service import LogMealRequestService
from api.services.log_permission_service import LogPermissionService
from api.services.log_user_service import LogUserService
from api.services.log_role_service import LogRoleService
from api.services.log_configuration_service import LogConfigurationService
from api.services.log_replication_service import LogReplicationService

# Domain User (AD Cache)
from api.services.domain_user_service import DomainUserService

__all__ = [
    # Auth
    "UserService",
    "SecurityUserService",
    "RoleService",
    "RevokedTokenService",
    "InternalTokenService",
    # Meal Request
    "MealTypeService",
    "MealRequestStatusService",
    "MealRequestService",
    # Organization
    "DepartmentService",
    "EmployeeService",
    "DepartmentAssignmentService",
    # External Systems
    "HRISService",
    "AttendanceSyncService",
    # Config
    "PageService",
    "PagePermissionService",
    "EmailService",
    "EmailRoleService",
    # Audit
    "LogAuthenticationService",
    "LogPermissionService",
    "LogMealRequestLineService",
    "LogMealRequestService",
    "LogUserService",
    "LogRoleService",
    "LogConfigurationService",
    "LogReplicationService",
    # Domain User (AD Cache)
    "DomainUserService",
]
