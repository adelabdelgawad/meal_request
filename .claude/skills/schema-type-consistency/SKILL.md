---
name: schema-type-consistency
description: |
  Create and modify Pydantic schemas (backend) and TypeScript types (frontend) while ensuring
  end-to-end type safety and CamelCase compliance. Use when creating response/request schemas,
  adding bilingual fields, generating TypeScript types from Pydantic schemas, creating Zod
  validation schemas, or ensuring API contracts match between frontend and backend.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# Schema & Type Consistency

## Overview

This skill ensures type safety between the FastAPI backend and Next.js frontend. The key challenge is maintaining consistent API contracts while handling:

- **CamelCase transformation** - Python snake_case ↔ JSON camelCase
- **Bilingual fields** - English/Arabic field naming conventions
- **Type alignment** - Pydantic ↔ TypeScript type definitions
- **Form validation** - Zod schemas matching backend constraints

> **CRITICAL**: All Pydantic schemas MUST inherit from `CamelModel`. Failure breaks frontend parsing.

## When to Use This Skill

Activate when request involves:

- Creating new Pydantic request/response schemas
- Creating TypeScript type definitions
- Adding bilingual fields (`name_en`, `name_ar`)
- Generating TypeScript types from Pydantic schemas
- Creating Zod validation schemas for forms
- Fixing frontend parsing errors
- Ensuring API contract consistency
- Adding datetime fields with timezone handling

## Quick Reference

### Backend Locations

| Component | Path |
|-----------|------|
| Base Schema | `src/backend/api/schemas/_base.py` |
| User Schemas | `src/backend/api/schemas/user_schemas.py` |
| Role Schemas | `src/backend/api/schemas/role_schemas.py` |
| All Schemas | `src/backend/api/schemas/*.py` |

### Frontend Locations

| Component | Path |
|-----------|------|
| Types Directory | `src/my-app/types/` |
| User Types | `src/my-app/types/user.ts` |
| Role Types | `src/my-app/types/role.ts` |
| Scheduler Types | `src/my-app/types/scheduler.ts` |
| Zod Schemas | `src/my-app/lib/validations/` |

## Core Pattern: CamelModel (MANDATORY)

### Backend Schema

```python
# src/backend/api/schemas/_base.py is the source of truth
from api.schemas._base import CamelModel
from typing import Optional
from datetime import datetime


class UserResponse(CamelModel):
    """
    Response schema for user data.

    Field names are snake_case in Python, automatically converted to
    camelCase in JSON responses.
    """
    id: str                              # → "id"
    username: str                        # → "username"
    full_name: Optional[str] = None      # → "fullName"
    is_active: bool                      # → "isActive"
    is_super_admin: bool = False         # → "isSuperAdmin"
    created_at: datetime                 # → "createdAt" (UTC with 'Z')
    updated_at: Optional[datetime] = None  # → "updatedAt"


class UserCreate(CamelModel):
    """Request schema for creating a user."""
    username: str
    full_name: Optional[str] = None
    is_active: bool = True
    role_ids: list[int] = []             # → "roleIds"
```

### Frontend TypeScript Type

```typescript
// src/my-app/types/user.ts

export interface User {
  id: string;
  username: string;
  fullName: string | null;
  isActive: boolean;
  isSuperAdmin: boolean;
  createdAt: string;  // ISO datetime string
  updatedAt: string | null;
}

export interface UserCreate {
  username: string;
  fullName?: string;
  isActive?: boolean;
  roleIds?: number[];
}
```

### Field Name Mapping

| Python (Backend) | JSON/TypeScript (Frontend) |
|-----------------|---------------------------|
| `user_id` | `userId` |
| `full_name` | `fullName` |
| `is_active` | `isActive` |
| `created_at` | `createdAt` |
| `role_ids` | `roleIds` |
| `name_en` | `nameEn` |
| `name_ar` | `nameAr` |

## Bilingual Field Pattern

### Backend Schema

```python
class RoleResponse(CamelModel):
    """Role with bilingual support."""
    id: int
    name_en: str                         # → "nameEn"
    name_ar: str                         # → "nameAr"
    description_en: Optional[str] = None # → "descriptionEn"
    description_ar: Optional[str] = None # → "descriptionAr"
    is_active: bool


class RoleCreate(CamelModel):
    """Create role with bilingual names."""
    name_en: str
    name_ar: str
    description_en: Optional[str] = None
    description_ar: Optional[str] = None
```

### Frontend TypeScript Type

```typescript
// src/my-app/types/role.ts

export interface Role {
  id: number;
  nameEn: string;
  nameAr: string;
  descriptionEn: string | null;
  descriptionAr: string | null;
  isActive: boolean;
}

export interface RoleCreate {
  nameEn: string;
  nameAr: string;
  descriptionEn?: string;
  descriptionAr?: string;
}

// Helper for displaying localized name
export function getLocalizedName(
  item: { nameEn: string; nameAr: string },
  locale: 'en' | 'ar'
): string {
  return locale === 'ar' ? item.nameAr : item.nameEn;
}
```

## Zod Validation Schema Pattern

### Frontend Zod Schema

```typescript
// src/my-app/lib/validations/role.ts
import { z } from 'zod';

export const roleCreateSchema = z.object({
  nameEn: z.string()
    .min(1, 'English name is required')
    .max(100, 'Name must be 100 characters or less'),
  nameAr: z.string()
    .min(1, 'Arabic name is required')
    .max(100, 'Name must be 100 characters or less'),
  descriptionEn: z.string().max(500).optional(),
  descriptionAr: z.string().max(500).optional(),
});

export type RoleCreateInput = z.infer<typeof roleCreateSchema>;

// For forms with react-hook-form
export const roleUpdateSchema = roleCreateSchema.partial();
```

### Using with React Hook Form

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { roleCreateSchema, RoleCreateInput } from '@/lib/validations/role';

function CreateRoleForm() {
  const form = useForm<RoleCreateInput>({
    resolver: zodResolver(roleCreateSchema),
    defaultValues: {
      nameEn: '',
      nameAr: '',
      descriptionEn: '',
      descriptionAr: '',
    },
  });

  const onSubmit = async (data: RoleCreateInput) => {
    // Data is validated and typed
    await createRole(data);
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)}>
      {/* form fields */}
    </form>
  );
}
```

## Paginated Response Pattern

### Backend Schema

```python
from typing import Generic, TypeVar, List
from api.schemas._base import CamelModel

T = TypeVar('T')


class PaginatedResponse(CamelModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool                       # → "hasNext"
    has_previous: bool                   # → "hasPrevious"


class UserListResponse(CamelModel):
    """Paginated user list with summary counts."""
    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    active_count: int                    # → "activeCount"
    inactive_count: int                  # → "inactiveCount"
```

### Frontend TypeScript Type

```typescript
// src/my-app/types/common.ts

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
}

// src/my-app/types/user.ts
export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  perPage: number;
  activeCount: number;
  inactiveCount: number;
}
```

## DateTime Handling

### Backend (UTC with 'Z' suffix)

```python
from datetime import datetime, timezone
from api.schemas._base import CamelModel


class AuditResponse(CamelModel):
    """Response with datetime fields."""
    id: str
    action: str
    created_at: datetime  # Auto-formatted as "2025-01-07T10:30:00Z"
    updated_at: Optional[datetime] = None
```

The `CamelModel` automatically:
1. Ensures datetimes are UTC-aware
2. Formats with 'Z' suffix instead of '+00:00'

### Frontend Parsing

```typescript
// Dates come as ISO strings with 'Z' suffix
interface AuditLog {
  id: string;
  action: string;
  createdAt: string;  // "2025-01-07T10:30:00Z"
  updatedAt: string | null;
}

// Parsing helper
function parseDateTime(isoString: string | null): Date | null {
  if (!isoString) return null;
  return new Date(isoString);
}

// Formatting helper (respects user locale)
function formatDateTime(
  isoString: string | null,
  locale: string = 'en'
): string {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleString(locale === 'ar' ? 'ar-SA' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}
```

## Allowed Operations

**DO:**
- Inherit all schemas from `CamelModel`
- Use snake_case for Python field names
- Use camelCase for TypeScript field names
- Create matching Zod schemas for form validation
- Include bilingual fields for user-facing data
- Use `Optional[T] = None` for nullable fields
- Specify `datetime` type for timestamp fields

**DON'T:**
- Inherit from `BaseModel` directly
- Use `Field(alias="camelCase")` manually
- Return `dict` without `by_alias=True`
- Mix snake_case in API responses
- Forget to create TypeScript types for new schemas
- Use string literals for datetime comparison

## Validation Checklist

Before completing schema work:

- [ ] All Pydantic schemas inherit from `CamelModel`
- [ ] No manual alias generators or Field aliases
- [ ] TypeScript types match schema structure
- [ ] Field names follow snake_case (Python) / camelCase (TS)
- [ ] Bilingual fields use `name_en`/`name_ar` pattern
- [ ] Optional fields have `= None` default
- [ ] DateTime fields are properly typed
- [ ] Zod schema matches backend constraints
- [ ] Response model specified on FastAPI endpoints

## Additional Resources

- [PATTERNS.md](PATTERNS.md) - Detailed code patterns
- [EXAMPLES.md](EXAMPLES.md) - Complete working examples
- [REFERENCE.md](REFERENCE.md) - API reference

## Trigger Phrases

- "Pydantic schema", "CamelModel", "response model"
- "TypeScript type", "type definition"
- "camelCase", "snake_case", "alias"
- "bilingual", "name_en", "name_ar"
- "Zod schema", "form validation"
- "API contract", "frontend parsing"
- "datetime", "timezone", "UTC"
