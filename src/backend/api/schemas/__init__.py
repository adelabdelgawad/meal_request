"""
API Schemas - Pydantic DTOs for all entities.

One schema module per entity following clean architecture.
"""

# Base Model (CRITICAL: All new schemas must inherit from CamelModel)
from api.schemas._base import CamelModel

# Auth Domain
from api.schemas.internal_auth_schemas import (
    InternalTokenBase,
    InternalTokenCreate,
    InternalTokenResponse,
    InternalTokenVerifyRequest,
    InternalTokenVerifyResponse,
    ServiceConfigResponse,
    ServiceHealthResponse,
)
from api.schemas.role_schemas import (
    RoleBase,
    RoleCreate,
    RolePageInfo,
    RolePagesResponse,
    RolePagesUpdate,
    RoleResponse,
    RoleStatusUpdate,
    RoleUpdate,
    RoleUserInfo,
    RoleUsersResponse,
    RoleUsersUpdate,
    SimpleRole,
)
from api.schemas.revoked_token_schemas import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RevokedTokenBase,
    RevokedTokenCreate,
    RevokedTokenResponse,
    TokenResponse,
)
from api.schemas.user_schemas import (
    UserBase,
    UserBlockUpdate,
    UserBulkStatusResponse,
    UserBulkStatusUpdate,
    UserCreate,
    UserListResponse,
    UserMarkManualRequest,
    UserResponse,
    UserRolesUpdate,
    UsersListResponse,
    UserStatusOverrideRequest,
    UserStatusOverrideResponse,
    UserStatusUpdate,
    UserUpdate,
)

# Meal Request Domain
from api.schemas.meal_request_line_schemas import (
    MealRequestLineBase,
    MealRequestLineCreate,
    MealRequestLineResponse,
    MealRequestLineUpdate,
)
from api.schemas.meal_request_schemas import (
    MealRequestBase,
    MealRequestCreate,
    MealRequestListResponse,
    MealRequestResponse,
    MealRequestUpdate,
)
from api.schemas.meal_request_status_schemas import (
    MealRequestStatusBase,
    MealRequestStatusCreate,
    MealRequestStatusResponse,
    MealRequestStatusUpdate,
)
from api.schemas.meal_type_schemas import (
    MealTypeBase,
    MealTypeCreate,
    MealTypeResponse,
    MealTypeUpdate,
)

# Organization Domain
from api.schemas.department_assignment_schemas import (
    DepartmentAssignmentBase,
    DepartmentAssignmentCreate,
    DepartmentAssignmentResponse,
    DepartmentAssignmentUpdate,
)
from api.schemas.department_schemas import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from api.schemas.employee_schemas import (
    EmployeeBase,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)

# Config Domain
from api.schemas.email_role_schemas import (
    EmailRoleBase,
    EmailRoleCreate,
    EmailRoleResponse,
    EmailRoleUpdate,
)
from api.schemas.email_schemas import (
    EmailBase,
    EmailCreate,
    EmailResponse,
    EmailUpdate,
)
from api.schemas.page_permission_schemas import (
    PagePermissionBase,
    PagePermissionCreate,
    PagePermissionResponse,
    PagePermissionUpdate,
)
from api.schemas.page_schemas import (
    PageBase,
    PageCreate,
    PageResponse,
    PageUpdate,
)

# Audit Domain
from api.schemas.log_authentication_schemas import (
    LogAuthenticationBase,
    LogAuthenticationCreate,
    LogAuthenticationList,
    LogAuthenticationQuery,
    LogAuthenticationResponse,
)
from api.schemas.log_meal_request_line_schemas import (
    LogMealRequestLineBase,
    LogMealRequestLineCreate,
    LogMealRequestLineResponse,
)
from api.schemas.log_meal_request_schemas import (
    LogMealRequestBase,
    LogMealRequestCreate,
    LogMealRequestList,
    LogMealRequestQuery,
    LogMealRequestResponse,
)
from api.schemas.log_permission_schemas import (
    LogPermissionBase,
    LogPermissionCreate,
    LogPermissionResponse,
)
from api.schemas.log_user_schemas import (
    LogUserCreate,
    LogUserList,
    LogUserQuery,
    LogUserResponse,
)
from api.schemas.log_role_schemas import (
    LogRoleCreate,
    LogRoleList,
    LogRoleQuery,
    LogRoleResponse,
)
from api.schemas.log_configuration_schemas import (
    LogConfigurationCreate,
    LogConfigurationList,
    LogConfigurationQuery,
    LogConfigurationResponse,
)
from api.schemas.log_replication_schemas import (
    LogReplicationBase,
    LogReplicationCreate,
    LogReplicationResponse,
)

# Domain User (AD Cache)
from api.schemas.domain_user_schemas import (
    DomainUserBase,
    DomainUserCreate,
    DomainUserListResponse,
    DomainUserResponse,
    DomainUserSyncResponse,
    DomainUserUpdate,
)

# HRIS Domain (External TMS Data)
from api.schemas.hris_schemas import (
    HRISAttendanceResponse,
    HRISShiftResponse,
)

# Scheduler Domain
from api.schemas.scheduler_schemas import (
    CleanupRequest,
    CleanupResponse,
    InstanceMode,
    InstanceStatus,
    JobAction,
    JobActionRequest,
    JobActionResponse,
    JobExecutionListResponse,
    JobExecutionResponse,
    ScheduledJobCreate,
    ScheduledJobCronCreate,
    ScheduledJobIntervalCreate,
    ScheduledJobListResponse,
    ScheduledJobResponse,
    ScheduledJobUpdate,
    SchedulerExecutionStatusListResponse,
    SchedulerExecutionStatusResponse,
    SchedulerInstanceResponse,
    SchedulerJobTypeListResponse,
    SchedulerJobTypeResponse,
    SchedulerStatusResponse,
    TaskFunctionListResponse,
    TaskFunctionResponse,
)

__all__ = [
    # Base Model
    "CamelModel",
    # Auth
    "UserBase",
    "UserBlockUpdate",
    "UserBulkStatusResponse",
    "UserBulkStatusUpdate",
    "UserCreate",
    "UserListResponse",
    "UserMarkManualRequest",
    "UserResponse",
    "UserRolesUpdate",
    "UsersListResponse",
    "UserStatusOverrideRequest",
    "UserStatusOverrideResponse",
    "UserStatusUpdate",
    "UserUpdate",
    "SimpleRole",
    "RoleBase",
    "RoleCreate",
    "RolePageInfo",
    "RolePagesResponse",
    "RolePagesUpdate",
    "RoleResponse",
    "RoleStatusUpdate",
    "RoleUpdate",
    "RoleUserInfo",
    "RoleUsersResponse",
    "RoleUsersUpdate",
    "RevokedTokenBase",
    "RevokedTokenCreate",
    "RevokedTokenResponse",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "LoginResponse",
    "InternalTokenBase",
    "InternalTokenCreate",
    "InternalTokenResponse",
    "InternalTokenVerifyRequest",
    "InternalTokenVerifyResponse",
    "ServiceHealthResponse",
    "ServiceConfigResponse",
    # Meal Request
    "MealTypeBase",
    "MealTypeCreate",
    "MealTypeResponse",
    "MealTypeUpdate",
    "MealRequestStatusBase",
    "MealRequestStatusCreate",
    "MealRequestStatusResponse",
    "MealRequestStatusUpdate",
    "MealRequestBase",
    "MealRequestCreate",
    "MealRequestResponse",
    "MealRequestUpdate",
    "MealRequestListResponse",
    "MealRequestLineBase",
    "MealRequestLineCreate",
    "MealRequestLineResponse",
    "MealRequestLineUpdate",
    # Organization
    "DepartmentBase",
    "DepartmentCreate",
    "DepartmentResponse",
    "DepartmentUpdate",
    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeResponse",
    "EmployeeUpdate",
    "DepartmentAssignmentBase",
    "DepartmentAssignmentCreate",
    "DepartmentAssignmentResponse",
    "DepartmentAssignmentUpdate",
    # Config
    "PageBase",
    "PageCreate",
    "PageResponse",
    "PageUpdate",
    "PagePermissionBase",
    "PagePermissionCreate",
    "PagePermissionResponse",
    "PagePermissionUpdate",
    "EmailBase",
    "EmailCreate",
    "EmailResponse",
    "EmailUpdate",
    "EmailRoleBase",
    "EmailRoleCreate",
    "EmailRoleResponse",
    "EmailRoleUpdate",
    # Audit
    "LogAuthenticationBase",
    "LogAuthenticationCreate",
    "LogAuthenticationList",
    "LogAuthenticationQuery",
    "LogAuthenticationResponse",
    "LogPermissionBase",
    "LogPermissionCreate",
    "LogPermissionResponse",
    "LogMealRequestLineBase",
    "LogMealRequestLineCreate",
    "LogMealRequestLineResponse",
    "LogMealRequestBase",
    "LogMealRequestCreate",
    "LogMealRequestList",
    "LogMealRequestQuery",
    "LogMealRequestResponse",
    "LogUserCreate",
    "LogUserList",
    "LogUserQuery",
    "LogUserResponse",
    "LogRoleCreate",
    "LogRoleList",
    "LogRoleQuery",
    "LogRoleResponse",
    "LogConfigurationCreate",
    "LogConfigurationList",
    "LogConfigurationQuery",
    "LogConfigurationResponse",
    "LogReplicationBase",
    "LogReplicationCreate",
    "LogReplicationResponse",
    # Authentication Audit Logs
    "LogAuthenticationBase",
    "LogAuthenticationCreate",
    "LogAuthenticationList",
    "LogAuthenticationQuery",
    "LogAuthenticationResponse",
    # Domain User (AD Cache)
    "DomainUserBase",
    "DomainUserCreate",
    "DomainUserListResponse",
    "DomainUserResponse",
    "DomainUserSyncResponse",
    "DomainUserUpdate",
    # HRIS (External TMS Data)
    "HRISAttendanceResponse",
    "HRISShiftResponse",
    # Scheduler
    "CleanupRequest",
    "CleanupResponse",
    "ExecutionStatus",
    "InstanceMode",
    "InstanceStatus",
    "JobAction",
    "JobActionRequest",
    "JobActionResponse",
    "JobExecutionListResponse",
    "JobExecutionResponse",
    "JobType",
    "ScheduledJobCreate",
    "ScheduledJobCronCreate",
    "ScheduledJobIntervalCreate",
    "ScheduledJobListResponse",
    "ScheduledJobResponse",
    "ScheduledJobUpdate",
    "SchedulerExecutionStatusListResponse",
    "SchedulerExecutionStatusResponse",
    "SchedulerInstanceResponse",
    "SchedulerJobTypeListResponse",
    "SchedulerJobTypeResponse",
    "SchedulerStatusResponse",
    "TaskFunctionListResponse",
    "TaskFunctionResponse",
]
