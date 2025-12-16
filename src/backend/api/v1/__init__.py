"""
API v1 - Router aggregation for all endpoints.

Organized by domain with proper HTTP methods and status codes.
"""

# Import all v1 routers
from api.v1 import (
    auth,
    login,
    me,
    navigation,
    meal_requests,
    meal_types,
    employees,
    departments,
    admin,
    audit,
    internal_auth,
    requests,
    permissions,
    analysis,
    reporting,
    domain_users,
    hris,
    settings,
)

__all__ = [
    "auth",
    "login",
    "me",
    "navigation",
    "meal_requests",
    "meal_types",
    "employees",
    "departments",
    "admin",
    "audit",
    "internal_auth",
    "requests",
    "permissions",
    "analysis",
    "reporting",
    "domain_users",
    "hris",
    "settings",
]
