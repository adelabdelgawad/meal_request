# RBAC Reference

Quick reference for role-based access control.

## File Locations

### Backend

| Component | Path |
|-----------|------|
| Models | `src/backend/db/models.py` |
| Role Service | `src/backend/api/services/role_service.py` |
| Page Service | `src/backend/api/services/page_service.py` |
| Permission Service | `src/backend/api/services/page_permission_service.py` |
| Log Role Service | `src/backend/api/services/log_role_service.py` |
| Log User Service | `src/backend/api/services/log_user_service.py` |
| Log Permission Service | `src/backend/api/services/log_permission_service.py` |
| Auth Utils | `src/backend/utils/auth.py` |
| Role Router | `src/backend/api/v1/router_role.py` |
| Permission Router | `src/backend/api/v1/router_permission_management.py` |

### Frontend

| Component | Path |
|-----------|------|
| Auth Context | `src/my-app/contexts/auth-context.tsx` |
| Navigation Config | `src/my-app/config/navigation.ts` |
| Role Management | `src/my-app/app/(pages)/roles/` |
| User Management | `src/my-app/app/(pages)/users/` |

## Models

### Role

```python
class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True)
    name_en = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    description_en = Column(Text, nullable=True)
    description_ar = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="role")
    page_permissions = relationship("PagePermission", back_populates="role")
```

### RolePermission

```python
class RolePermission(Base):
    __tablename__ = "role_permission"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("user.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    role = relationship("Role", back_populates="role_permissions")
```

### PagePermission

```python
class PagePermission(Base):
    __tablename__ = "page_permission"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("role.id"), nullable=False)
    page_id = Column(Integer, ForeignKey("page.id"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("user.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    role = relationship("Role", back_populates="page_permissions")
    page = relationship("Page", back_populates="page_permissions")
```

### Page

```python
class Page(Base):
    __tablename__ = "page"

    id = Column(Integer, primary_key=True)
    name_en = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    route = Column(String(255), nullable=False, unique=True)
    icon = Column(String(50), nullable=True)
    parent_id = Column(Integer, ForeignKey("page.id"), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Relationships
    parent = relationship("Page", remote_side=[id])
    page_permissions = relationship("PagePermission", back_populates="page")
```

## Auth Dependencies

| Dependency | Purpose |
|------------|---------|
| `get_current_user` | Get authenticated user from JWT |
| `get_current_super_admin` | Require super admin role |
| `require_role("name")` | Require specific role |
| `require_any_role(["a", "b"])` | Require any of specified roles |

## API Endpoints

### Roles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/roles` | List roles |
| POST | `/api/v1/roles` | Create role |
| GET | `/api/v1/roles/{id}` | Get role |
| PUT | `/api/v1/roles/{id}` | Update role |
| DELETE | `/api/v1/roles/{id}` | Delete role |
| GET | `/api/v1/roles/{id}/users` | Get users with role |
| PUT | `/api/v1/roles/{id}/users` | Update role users |
| GET | `/api/v1/roles/{id}/pages` | Get role pages |
| PUT | `/api/v1/roles/{id}/pages` | Update role pages |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/{id}/roles` | Get user roles |
| PUT | `/api/v1/users/{id}/roles` | Update user roles |

### Pages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pages` | List pages |
| GET | `/api/v1/navigation` | Get user's accessible pages |

## Audit Log Actions

### Role Actions

| Action | Description |
|--------|-------------|
| `CREATE` | Role created |
| `UPDATE` | Role modified |
| `DELETE` | Role deleted |
| `STATUS_CHANGE` | Role activated/deactivated |

### Permission Actions

| Action | Description |
|--------|-------------|
| `ROLE_ASSIGNED` | Role assigned to user |
| `ROLE_REVOKED` | Role removed from user |
| `PAGE_ASSIGNED` | Page assigned to role |
| `PAGE_REVOKED` | Page removed from role |

## Common Queries

### Get User Roles

```python
async def get_user_roles(session: AsyncSession, user_id: str) -> list[str]:
    query = (
        select(Role.name_en)
        .join(RolePermission, Role.id == RolePermission.role_id)
        .where(
            RolePermission.user_id == user_id,
            Role.is_active == True
        )
    )
    result = await session.execute(query)
    return [row[0] for row in result.all()]
```

### Get User Pages

```python
async def get_user_pages(session: AsyncSession, user_id: str) -> list[str]:
    query = (
        select(Page.route)
        .join(PagePermission, Page.id == PagePermission.page_id)
        .join(RolePermission, PagePermission.role_id == RolePermission.role_id)
        .where(
            RolePermission.user_id == user_id,
            Page.is_active == True
        )
    )
    result = await session.execute(query)
    return list(set(row[0] for row in result.all()))
```

### Check Page Access

```python
async def check_page_access(
    session: AsyncSession,
    user_id: str,
    route: str,
) -> bool:
    query = (
        select(func.count())
        .select_from(PagePermission)
        .join(RolePermission, PagePermission.role_id == RolePermission.role_id)
        .join(Page, PagePermission.page_id == Page.id)
        .where(
            RolePermission.user_id == user_id,
            Page.route == route,
            Page.is_active == True
        )
    )
    count = await session.scalar(query)
    return count > 0
```

## Frontend Patterns

### Auth Context

```typescript
interface AuthContextValue {
  user: User | null;
  userRoles: string[];
  userPages: string[];
  isLoading: boolean;
  hasRole: (role: string) => boolean;
  hasPage: (route: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}
```

### Navigation Filter

```typescript
function getNavigationItems(userPages: string[], isSuperAdmin: boolean) {
  return navigationItems.filter((item) => {
    if (isSuperAdmin) return true;
    return userPages.includes(item.route);
  });
}
```

### Route Protection

```typescript
// middleware.ts or layout.tsx
if (!userPages.includes(pathname) && !user.isSuperAdmin) {
  redirect('/unauthorized');
}
```

## Best Practices

1. **Always audit log** - Every permission change must be logged
2. **Check at both layers** - Backend and frontend permission checks
3. **Use super admin bypass** - Super admin skips permission checks
4. **Bilingual names** - Roles and pages need English and Arabic names
5. **Soft delete roles** - Use is_active instead of hard delete
6. **Cache permissions** - Store user roles in JWT token
