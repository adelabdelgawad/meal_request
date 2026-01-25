# Schema & Type Consistency Patterns

Critical patterns for maintaining type safety between backend and frontend.

## CamelModel Base Class

All schemas must inherit from `CamelModel`:

```python
# src/backend/api/schemas/_base.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from utils.datetime_utils import ensure_utc


class CamelModel(BaseModel):
    """
    Base model that enforces camelCase aliases and UTC datetime serialization.

    Configuration:
        - alias_generator=to_camel: Generates camelCase from snake_case
        - populate_by_name=True: Accepts both snake_case and camelCase input
        - serialize_by_alias=True: Outputs camelCase in JSON
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        serialize_by_alias=True,
    )

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        """Override to ensure datetimes are UTC with 'Z' suffix."""
        data = super().model_dump(**kwargs)
        return self._process_datetimes(data)

    @classmethod
    def _process_datetimes(cls, data: Any) -> Any:
        """Recursively convert datetimes to UTC ISO format."""
        if isinstance(data, datetime):
            utc_dt = ensure_utc(data)
            return utc_dt.isoformat().replace('+00:00', 'Z')
        elif isinstance(data, dict):
            return {key: cls._process_datetimes(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [cls._process_datetimes(item) for item in data]
        return data
```

---

## Request Schema Pattern

For data coming from the frontend:

```python
from typing import Optional, List
from api.schemas._base import CamelModel


class UserCreateRequest(CamelModel):
    """
    Request schema for creating a user.

    Frontend sends camelCase, backend receives snake_case via populate_by_name.
    """
    username: str
    full_name: Optional[str] = None
    is_active: bool = True
    role_ids: List[int] = []


class UserUpdateRequest(CamelModel):
    """
    Request schema for updating a user.

    All fields optional for partial updates.
    """
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None
```

---

## Response Schema Pattern

For data going to the frontend:

```python
from typing import Optional, List
from datetime import datetime
from api.schemas._base import CamelModel


class UserResponse(CamelModel):
    """
    Response schema for user data.

    Backend outputs snake_case, serializes to camelCase for frontend.
    """
    id: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_super_admin: bool
    created_at: datetime
    updated_at: Optional[datetime]

    # Nested objects
    role: Optional['RoleResponse'] = None


class UserListResponse(CamelModel):
    """Paginated user list with counts."""
    items: List[UserResponse]
    total: int
    page: int
    per_page: int
    active_count: int
    inactive_count: int
```

---

## Bilingual Schema Pattern

For entities with English and Arabic names:

```python
from typing import Optional
from api.schemas._base import CamelModel


class BilingualEntityCreate(CamelModel):
    """Base for creating bilingual entities."""
    name_en: str
    name_ar: str
    description_en: Optional[str] = None
    description_ar: Optional[str] = None


class BilingualEntityResponse(CamelModel):
    """Base for bilingual entity responses."""
    id: int
    name_en: str
    name_ar: str
    description_en: Optional[str]
    description_ar: Optional[str]
    is_active: bool


# Concrete implementations
class RoleCreate(BilingualEntityCreate):
    """Create a role."""
    pass


class RoleResponse(BilingualEntityResponse):
    """Role response."""
    users_count: int = 0
    pages_count: int = 0


class DepartmentCreate(BilingualEntityCreate):
    """Create a department."""
    parent_id: Optional[int] = None


class DepartmentResponse(BilingualEntityResponse):
    """Department response."""
    parent_id: Optional[int]
    children_count: int = 0
```

---

## Nested Schema Pattern

For schemas with relationships:

```python
from typing import Optional, List
from api.schemas._base import CamelModel


class RoleBasicResponse(CamelModel):
    """Minimal role info for embedding."""
    id: int
    name_en: str
    name_ar: str


class UserWithRolesResponse(CamelModel):
    """User with embedded role information."""
    id: str
    username: str
    full_name: Optional[str]
    is_active: bool
    roles: List[RoleBasicResponse]  # Nested list


class MealRequestResponse(CamelModel):
    """Meal request with nested relationships."""
    id: int
    request_date: datetime
    status: 'MealRequestStatusResponse'  # Forward reference
    requester: 'UserBasicResponse'
    lines: List['MealRequestLineResponse']
```

---

## TypeScript Type Generation Pattern

Manually create matching TypeScript types:

### Backend Schema

```python
# src/backend/api/schemas/scheduler_schemas.py
from typing import Optional, List
from datetime import datetime
from api.schemas._base import CamelModel


class ScheduledJobResponse(CamelModel):
    """Scheduled job details."""
    id: int
    job_name: str
    job_type_id: int
    task_function_id: int
    is_enabled: bool
    is_active: bool
    priority: int
    max_instances: int
    misfire_grace_time: int
    coalesce: bool
    interval_seconds: Optional[int]
    interval_minutes: Optional[int]
    interval_hours: Optional[int]
    interval_days: Optional[int]
    cron_expression: Optional[str]
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
```

### Frontend TypeScript Type

```typescript
// src/my-app/types/scheduler.ts

export interface ScheduledJob {
  id: number;
  jobName: string;
  jobTypeId: number;
  taskFunctionId: number;
  isEnabled: boolean;
  isActive: boolean;
  priority: number;
  maxInstances: number;
  misfireGraceTime: number;
  coalesce: boolean;
  intervalSeconds: number | null;
  intervalMinutes: number | null;
  intervalHours: number | null;
  intervalDays: number | null;
  cronExpression: string | null;
  nextRunAt: string | null;
  lastRunAt: string | null;
  createdAt: string;
  updatedAt: string | null;
}
```

---

## Zod Schema Pattern

For form validation:

```typescript
// src/my-app/lib/validations/scheduler.ts
import { z } from 'zod';

// Job type enum matching backend
export const JobType = {
  INTERVAL: 1,
  CRON: 2,
} as const;

export const scheduledJobCreateSchema = z.object({
  jobName: z.string()
    .min(1, 'Job name is required')
    .max(255, 'Job name must be 255 characters or less'),
  jobTypeId: z.number()
    .int()
    .refine((v) => v === JobType.INTERVAL || v === JobType.CRON, {
      message: 'Invalid job type',
    }),
  taskFunctionId: z.number().int().positive('Task function is required'),
  isEnabled: z.boolean().default(true),
  priority: z.number().int().min(0).max(100).default(0),
  maxInstances: z.number().int().min(1).max(10).default(1),
  misfireGraceTime: z.number().int().min(0).max(3600).default(60),
  coalesce: z.boolean().default(true),

  // Interval fields (mutually exclusive with cron)
  intervalSeconds: z.number().int().min(1).optional(),
  intervalMinutes: z.number().int().min(1).optional(),
  intervalHours: z.number().int().min(1).optional(),
  intervalDays: z.number().int().min(1).optional(),

  // Cron field (mutually exclusive with interval)
  cronExpression: z.string()
    .regex(/^[\d\s\*\-\/\,]+$/, 'Invalid cron expression')
    .optional(),
}).superRefine((data, ctx) => {
  // Validate interval OR cron, not both
  const hasInterval = data.intervalSeconds || data.intervalMinutes ||
                      data.intervalHours || data.intervalDays;
  const hasCron = data.cronExpression;

  if (data.jobTypeId === JobType.INTERVAL && !hasInterval) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Interval jobs require at least one interval field',
      path: ['intervalSeconds'],
    });
  }

  if (data.jobTypeId === JobType.CRON && !hasCron) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Cron jobs require a cron expression',
      path: ['cronExpression'],
    });
  }
});

export type ScheduledJobCreateInput = z.infer<typeof scheduledJobCreateSchema>;
```

---

## Enum Schema Pattern

### Backend Enum Response

```python
from enum import IntEnum
from api.schemas._base import CamelModel


class JobTypeEnum(IntEnum):
    INTERVAL = 1
    CRON = 2


class JobTypeResponse(CamelModel):
    """Job type lookup."""
    id: int
    code: str
    name_en: str
    name_ar: str


class ExecutionStatusEnum(IntEnum):
    PENDING = 1
    RUNNING = 2
    SUCCESS = 3
    FAILED = 4
    CANCELLED = 5
```

### Frontend TypeScript Enum

```typescript
// src/my-app/types/scheduler.ts

export const JobType = {
  INTERVAL: 1,
  CRON: 2,
} as const;

export type JobTypeId = typeof JobType[keyof typeof JobType];

export const ExecutionStatus = {
  PENDING: 1,
  RUNNING: 2,
  SUCCESS: 3,
  FAILED: 4,
  CANCELLED: 5,
} as const;

export type ExecutionStatusId = typeof ExecutionStatus[keyof typeof ExecutionStatus];

// Helper for status labels
export const ExecutionStatusLabel: Record<ExecutionStatusId, string> = {
  [ExecutionStatus.PENDING]: 'Pending',
  [ExecutionStatus.RUNNING]: 'Running',
  [ExecutionStatus.SUCCESS]: 'Success',
  [ExecutionStatus.FAILED]: 'Failed',
  [ExecutionStatus.CANCELLED]: 'Cancelled',
};
```

---

## FastAPI Endpoint Pattern

Properly typed endpoints:

```python
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from api.schemas.user_schemas import (
    UserResponse,
    UserCreateRequest,
    UserUpdateRequest,
    UserListResponse,
)
from api.services.user_service import UserService
from db.maria_database import get_session
from utils.auth import get_current_super_admin
from db.models import Account

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users with optional filters.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by username or name"),
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
) -> UserListResponse:
    """Get paginated user list."""
    return await user_service.list_users(
        session,
        page=page,
        per_page=per_page,
        is_active=is_active,
        search=search,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
async def create_user(
    request: UserCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
) -> UserResponse:
    """Create a new user."""
    return await user_service.create_user(
        session,
        request,
        created_by_id=str(current_user.id),
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
) -> UserResponse:
    """Update an existing user."""
    return await user_service.update_user(
        session,
        user_id,
        request,
        updated_by_id=str(current_user.id),
    )
```

---

## Anti-Patterns to Avoid

### 1. Inheriting from BaseModel

```python
# ❌ WRONG - Missing camelCase conversion
from pydantic import BaseModel

class UserResponse(BaseModel):  # ❌
    user_id: str  # Will serialize as "user_id", not "userId"
```

### 2. Manual Alias Configuration

```python
# ❌ WRONG - Duplicates CamelModel functionality
from pydantic import Field

class UserResponse(CamelModel):
    user_id: str = Field(alias="userId")  # ❌ Unnecessary
```

### 3. Inconsistent Field Naming

```python
# ❌ WRONG - Mixed conventions
class UserResponse(CamelModel):
    userId: str      # ❌ Should be user_id
    full_name: str   # ✅ Correct
```

### 4. Missing TypeScript Types

```typescript
// ❌ WRONG - Using any
async function getUsers(): Promise<any> {  // ❌
  return await api.get('/users');
}

// ✅ CORRECT
async function getUsers(): Promise<UserListResponse> {
  return await api.get<UserListResponse>('/users');
}
```

### 5. Mismatched Types

```python
# Backend
class UserResponse(CamelModel):
    role_ids: List[int]  # List of integers

# Frontend - WRONG
interface User {
  roleIds: string[];  // ❌ Should be number[]
}
```

---

## Type Mapping Reference

| Python Type | TypeScript Type | Notes |
|------------|-----------------|-------|
| `str` | `string` | |
| `int` | `number` | |
| `float` | `number` | |
| `bool` | `boolean` | |
| `None` | `null` | |
| `Optional[T]` | `T \| null` | |
| `List[T]` | `T[]` | |
| `Dict[str, T]` | `Record<string, T>` | |
| `datetime` | `string` | ISO format with 'Z' |
| `date` | `string` | ISO date format |
| `UUID` | `string` | |
| `Enum` | `const object` | See enum pattern |

---

## Validation Checklist

- [ ] Schema inherits from `CamelModel`
- [ ] No manual alias generators
- [ ] TypeScript type matches schema
- [ ] Field names are snake_case (Python)
- [ ] Nullable fields use `Optional[T] = None`
- [ ] DateTime fields use `datetime` type
- [ ] Zod schema matches backend constraints
- [ ] FastAPI endpoint has `response_model`
