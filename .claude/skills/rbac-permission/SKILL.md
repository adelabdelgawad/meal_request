---
name: rbac-permission
description: |
  Manage role-based access control, page permissions, and audit logging patterns.
  Use when adding new pages with permissions, creating roles, implementing audit logging,
  checking permission coverage, or updating navigation based on permissions.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# RBAC & Permission Management

## Overview

This skill helps manage the role-based access control system including:

- **Roles** - Named permission groups (e.g., admin, requester, ordertaker)
- **Role Permissions** - User-to-role assignments
- **Page Permissions** - Role-to-page access mapping
- **Audit Logging** - Recording all permission changes

> **CRITICAL**: All mutations to users, roles, and permissions MUST include audit logging.

## When to Use This Skill

Activate when request involves:

- Creating new roles with permissions
- Adding new pages with access control
- Assigning roles to users
- Implementing permission checks in endpoints
- Adding audit logging for operations
- Updating frontend navigation permissions
- Checking permission coverage

## Quick Reference

### Backend Locations

| Component | Path |
|-----------|------|
| Models | `src/backend/db/models.py` (Role, RolePermission, PagePermission, Page) |
| Role Service | `src/backend/api/services/role_service.py` |
| Page Service | `src/backend/api/services/page_service.py` |
| Permission Service | `src/backend/api/services/page_permission_service.py` |
| Log Services | `src/backend/api/services/log_*_service.py` |
| Auth Utils | `src/backend/utils/auth.py` |
| Permission Router | `src/backend/api/v1/router_permission_management.py` |

### Frontend Locations

| Component | Path |
|-----------|------|
| Auth Context | `src/my-app/contexts/auth-context.tsx` |
| Navigation Config | `src/my-app/config/navigation.ts` |
| Permission Guards | `src/my-app/components/permission-guard.tsx` |
| Role Management | `src/my-app/app/(pages)/roles/` |

## Core Models

### Database Schema

```
User (user)
├── id: UUID
├── username: str
├── is_super_admin: bool
└── role_permissions: [RolePermission]

Role (role)
├── id: int
├── name_en: str
├── name_ar: str
├── is_active: bool
├── role_permissions: [RolePermission]
└── page_permissions: [PagePermission]

RolePermission (role_permission)
├── id: int
├── user_id: UUID (FK -> user)
├── role_id: int (FK -> role)
└── created_by_id: UUID

PagePermission (page_permission)
├── id: int
├── role_id: int (FK -> role)
├── page_id: int (FK -> page)
└── created_by_id: UUID

Page (page)
├── id: int
├── name_en: str
├── name_ar: str
├── route: str
├── icon: str
├── parent_id: int (FK -> page, for nested nav)
└── is_active: bool
```

## Permission Check Pattern

### Backend Endpoint Protection

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Account
from db.maria_database import get_session
from utils.auth import (
    get_current_user,
    get_current_super_admin,
    require_role,
    require_any_role,
)

router = APIRouter(prefix="/meals", tags=["Meal Requests"])


# Super admin only
@router.get("/admin-only")
async def admin_only_endpoint(
    current_user: Account = Depends(get_current_super_admin),
):
    """Only super admins can access."""
    ...


# Specific role required
@router.get("/ordertaker-only")
async def ordertaker_endpoint(
    current_user: Account = Depends(require_role("ordertaker")),
):
    """Only ordertaker role can access."""
    ...


# Any of multiple roles
@router.get("/meal-managers")
async def meal_managers_endpoint(
    current_user: Account = Depends(require_any_role(["ordertaker", "admin"])),
):
    """Ordertaker or admin can access."""
    ...


# Custom permission check
@router.get("/custom-check")
async def custom_permission_endpoint(
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_user),
):
    """Custom permission logic."""
    from api.services.page_permission_service import PagePermissionService

    permission_service = PagePermissionService()
    has_access = await permission_service.check_user_page_access(
        session,
        user_id=str(current_user.id),
        page_route="/meals",
    )

    if not has_access and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this resource",
        )
    ...
```

### Auth Utility Functions

```python
# utils/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db.models import Account

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Account:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)

    user = await get_user_by_id(session, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_super_admin(
    current_user: Account = Depends(get_current_user),
) -> Account:
    """Require super admin role."""
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


def require_role(role_name: str):
    """Create dependency that requires specific role."""
    async def check_role(
        current_user: Account = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> Account:
        roles = await get_user_roles(session, str(current_user.id))
        if role_name not in roles and not current_user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required",
            )
        return current_user
    return check_role


def require_any_role(role_names: list[str]):
    """Create dependency that requires any of the specified roles."""
    async def check_roles(
        current_user: Account = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> Account:
        user_roles = await get_user_roles(session, str(current_user.id))
        if not any(r in user_roles for r in role_names) and not current_user.is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {role_names} required",
            )
        return current_user
    return check_roles
```

## Audit Logging Pattern

### Service Method with Audit

```python
# api/services/role_service.py

from api.services.log_role_service import LogRoleService

class RoleService:
    def __init__(self):
        self._repo = RoleRepository()
        self._log_service = LogRoleService()

    async def create_role(
        self,
        session: AsyncSession,
        data: RoleCreate,
        created_by_id: str,
    ) -> Role:
        """Create role with audit logging."""
        # Create the role
        role = await self._repo.create(session, Role(**data.model_dump()))

        # Log the creation
        await self._log_service.log_create(
            session,
            role_id=role.id,
            role_name=role.name_en,
            created_by_id=created_by_id,
            details={
                "name_en": role.name_en,
                "name_ar": role.name_ar,
            },
        )

        return role

    async def update_role(
        self,
        session: AsyncSession,
        role_id: int,
        data: RoleUpdate,
        updated_by_id: str,
    ) -> Role:
        """Update role with audit logging."""
        # Get current state for logging
        old_role = await self._repo.get_by_id(session, role_id)
        if not old_role:
            raise NotFoundError(entity="Role", identifier=role_id)

        old_values = {
            "name_en": old_role.name_en,
            "name_ar": old_role.name_ar,
            "is_active": old_role.is_active,
        }

        # Update the role
        role = await self._repo.update(session, role_id, data.model_dump(exclude_unset=True))

        new_values = {
            "name_en": role.name_en,
            "name_ar": role.name_ar,
            "is_active": role.is_active,
        }

        # Log the update
        await self._log_service.log_update(
            session,
            role_id=role.id,
            role_name=role.name_en,
            updated_by_id=updated_by_id,
            old_values=old_values,
            new_values=new_values,
        )

        return role

    async def assign_role_to_user(
        self,
        session: AsyncSession,
        user_id: str,
        role_id: int,
        assigned_by_id: str,
    ) -> RolePermission:
        """Assign role with audit logging."""
        # Create assignment
        permission = await self._role_permission_repo.assign(
            session, user_id=user_id, role_id=role_id
        )

        # Log assignment
        await self._log_service.log_role_assignment(
            session,
            user_id=user_id,
            role_id=role_id,
            assigned_by_id=assigned_by_id,
            action="assigned",
        )

        return permission
```

### Log Service Structure

```python
# api/services/log_role_service.py

from db.models import LogRole


class LogRoleService:
    """Service for logging role changes."""

    async def log_create(
        self,
        session: AsyncSession,
        role_id: int,
        role_name: str,
        created_by_id: str,
        details: dict,
    ) -> LogRole:
        """Log role creation."""
        log = LogRole(
            action="CREATE",
            role_id=role_id,
            role_name=role_name,
            created_by_id=created_by_id,
            new_values=details,
        )
        session.add(log)
        await session.flush()
        return log

    async def log_update(
        self,
        session: AsyncSession,
        role_id: int,
        role_name: str,
        updated_by_id: str,
        old_values: dict,
        new_values: dict,
    ) -> LogRole:
        """Log role update."""
        # Only log changed fields
        changes = {
            k: {"old": old_values.get(k), "new": v}
            for k, v in new_values.items()
            if old_values.get(k) != v
        }

        if not changes:
            return None  # No actual changes

        log = LogRole(
            action="UPDATE",
            role_id=role_id,
            role_name=role_name,
            created_by_id=updated_by_id,
            old_values=old_values,
            new_values=new_values,
            changes=changes,
        )
        session.add(log)
        await session.flush()
        return log
```

## Frontend Permission Guard

```typescript
// components/permission-guard.tsx
"use client";

import { useAuth } from "@/contexts/auth-context";
import { ReactNode } from "react";

interface PermissionGuardProps {
  children: ReactNode;
  requiredRoles?: string[];
  requiredPages?: string[];
  fallback?: ReactNode;
}

export function PermissionGuard({
  children,
  requiredRoles = [],
  requiredPages = [],
  fallback = null,
}: PermissionGuardProps) {
  const { user, userRoles, userPages } = useAuth();

  // Super admin bypasses all checks
  if (user?.isSuperAdmin) {
    return <>{children}</>;
  }

  // Check role requirements
  if (requiredRoles.length > 0) {
    const hasRole = requiredRoles.some((role) => userRoles.includes(role));
    if (!hasRole) {
      return <>{fallback}</>;
    }
  }

  // Check page requirements
  if (requiredPages.length > 0) {
    const hasPage = requiredPages.some((page) => userPages.includes(page));
    if (!hasPage) {
      return <>{fallback}</>;
    }
  }

  return <>{children}</>;
}

// Usage
<PermissionGuard requiredRoles={["admin", "ordertaker"]}>
  <AdminButton />
</PermissionGuard>
```

## Adding a New Page with Permissions

### Step 1: Create Page Record

```sql
INSERT INTO page (name_en, name_ar, route, icon, is_active)
VALUES ('Reports', 'التقارير', '/reports', 'chart-bar', TRUE);
```

### Step 2: Assign to Roles

```python
# Migration or seed script
from db.models import PagePermission

# Assign to admin role
permission = PagePermission(
    role_id=1,  # admin role
    page_id=new_page_id,
    created_by_id=system_user_id,
)
session.add(permission)
```

### Step 3: Add Frontend Route

```typescript
// config/navigation.ts
export const navigationItems = [
  // ...existing items
  {
    route: "/reports",
    labelEn: "Reports",
    labelAr: "التقارير",
    icon: ChartBarIcon,
    requiredRoles: ["admin"],
  },
];
```

### Step 4: Protect Backend Endpoint

```python
@router.get("/reports")
async def get_reports(
    current_user: Account = Depends(require_any_role(["admin"])),
):
    ...
```

## Allowed Operations

**DO:**
- Include audit logging in all permission mutations
- Use dependency injection for permission checks
- Check permissions at both backend and frontend
- Log old and new values for updates
- Use bilingual names for roles and pages

**DON'T:**
- Skip audit logging for any mutation
- Hardcode permission checks in routes
- Store sensitive data in audit logs
- Forget frontend permission guards
- Allow direct database modifications

## Validation Checklist

Before completing RBAC work:

- [ ] Backend endpoint has permission check
- [ ] Audit logging included for all mutations
- [ ] Frontend has permission guard
- [ ] Navigation config updated
- [ ] Page record exists in database
- [ ] Role-page permissions assigned
- [ ] Tests cover permission scenarios

## Additional Resources

- [PATTERNS.md](PATTERNS.md) - Detailed permission patterns
- [REFERENCE.md](REFERENCE.md) - API reference

## Trigger Phrases

- "role", "permission", "RBAC"
- "page access", "route protection"
- "audit log", "log service"
- "assign role", "revoke role"
- "super admin", "require role"
- "navigation", "menu items"
