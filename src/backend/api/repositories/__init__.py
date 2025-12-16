"""
API Repositories - Data access layer for all entities.

One repository module per entity following clean architecture.
"""

# Auth Domain
from api.repositories.revoked_token_repository import RevokedTokenRepository
from api.repositories.role_repository import RoleRepository
from api.repositories.user_repository import UserRepository

# Meal Request Domain
from api.repositories.meal_request_line_repository import (
    MealRequestLineRepository,
)
from api.repositories.meal_request_repository import MealRequestRepository
from api.repositories.meal_request_status_repository import (
    MealRequestStatusRepository,
)
from api.repositories.meal_type_repository import MealTypeRepository

# Organization Domain
from api.repositories.department_assignment_repository import (
    DepartmentAssignmentRepository,
)
from api.repositories.department_repository import DepartmentRepository
from api.repositories.employee_repository import EmployeeRepository

# Config Domain
from api.repositories.email_repository import EmailRepository
from api.repositories.email_role_repository import EmailRoleRepository
from api.repositories.page_permission_repository import PagePermissionRepository
from api.repositories.page_repository import PageRepository

# Audit Domain
from api.repositories.log_authentication_repository import (
    LogAuthenticationRepository,
)
from api.repositories.log_meal_request_line_repository import (
    LogMealRequestLineRepository,
)
from api.repositories.log_meal_request_repository import LogMealRequestRepository
from api.repositories.log_permission_repository import LogPermissionRepository
from api.repositories.log_user_repository import LogUserRepository
from api.repositories.log_role_repository import LogRoleRepository
from api.repositories.log_configuration_repository import (
    LogConfigurationRepository,
)
from api.repositories.log_replication_repository import LogReplicationRepository

__all__ = [
    # Auth
    "UserRepository",
    "RoleRepository",
    "RevokedTokenRepository",
    # Meal Request
    "MealTypeRepository",
    "MealRequestStatusRepository",
    "MealRequestRepository",
    "MealRequestLineRepository",
    # Organization
    "DepartmentRepository",
    "EmployeeRepository",
    "DepartmentAssignmentRepository",
    # Config
    "PageRepository",
    "PagePermissionRepository",
    "EmailRepository",
    "EmailRoleRepository",
    # Audit
    "LogAuthenticationRepository",
    "LogPermissionRepository",
    "LogMealRequestLineRepository",
    "LogMealRequestRepository",
    "LogUserRepository",
    "LogRoleRepository",
    "LogConfigurationRepository",
    "LogReplicationRepository",
]
