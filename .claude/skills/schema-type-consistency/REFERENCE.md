# Schema & Type Consistency Reference

Quick reference for schema and type development.

## File Locations

### Backend Schemas

| Schema | Path |
|--------|------|
| Base (CamelModel) | `src/backend/api/schemas/_base.py` |
| User Schemas | `src/backend/api/schemas/user_schemas.py` |
| Role Schemas | `src/backend/api/schemas/role_schemas.py` |
| Auth Schemas | `src/backend/api/schemas/auth_schemas.py` |
| Scheduler Schemas | `src/backend/api/schemas/scheduler_schemas.py` |
| Meal Request Schemas | `src/backend/api/schemas/meal_request_schemas.py` |

### Frontend Types

| Type | Path |
|------|------|
| User Types | `src/my-app/types/user.ts` |
| Role Types | `src/my-app/types/role.ts` |
| Auth Types | `src/my-app/types/auth.ts` |
| Scheduler Types | `src/my-app/types/scheduler.ts` |
| Common Types | `src/my-app/types/common.ts` |

### Zod Validations

| Validation | Path |
|------------|------|
| User Validations | `src/my-app/lib/validations/user.ts` |
| Role Validations | `src/my-app/lib/validations/role.ts` |
| Scheduler Validations | `src/my-app/lib/validations/scheduler.ts` |

## CamelModel Configuration

```python
model_config = ConfigDict(
    alias_generator=to_camel,      # snake_case → camelCase
    populate_by_name=True,         # Accept both formats
    from_attributes=True,          # ORM model support
    serialize_by_alias=True,       # Output camelCase
)
```

## Field Type Mapping

| Python | TypeScript | JSON |
|--------|------------|------|
| `str` | `string` | `"value"` |
| `int` | `number` | `123` |
| `float` | `number` | `12.34` |
| `bool` | `boolean` | `true` |
| `None` | `null` | `null` |
| `Optional[str]` | `string \| null` | `"value"` or `null` |
| `List[int]` | `number[]` | `[1, 2, 3]` |
| `Dict[str, Any]` | `Record<string, any>` | `{"key": "value"}` |
| `datetime` | `string` | `"2025-01-07T10:30:00Z"` |
| `date` | `string` | `"2025-01-07"` |
| `UUID` | `string` | `"550e8400-e29b-41d4-a716-446655440000"` |

## Bilingual Field Convention

| Purpose | English Field | Arabic Field |
|---------|---------------|--------------|
| Name | `name_en` | `name_ar` |
| Description | `description_en` | `description_ar` |
| Title | `title_en` | `title_ar` |
| Label | `label_en` | `label_ar` |

## Common Schema Patterns

### Simple Response

```python
class ItemResponse(CamelModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime
```

### Paginated Response

```python
class ItemListResponse(CamelModel):
    items: List[ItemResponse]
    total: int
    page: int
    per_page: int
```

### Create Request

```python
class ItemCreate(CamelModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
```

### Update Request

```python
class ItemUpdate(CamelModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
```

## Zod Common Patterns

### Required String

```typescript
z.string().min(1, 'Required')
```

### Optional String

```typescript
z.string().optional()
```

### Email

```typescript
z.string().email('Invalid email')
```

### Number Range

```typescript
z.number().int().min(1).max(100)
```

### Enum

```typescript
z.enum(['option1', 'option2', 'option3'])
```

### Array

```typescript
z.array(z.number().int())
```

### Conditional Validation

```typescript
z.object({
  type: z.enum(['a', 'b']),
  fieldA: z.string().optional(),
  fieldB: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.type === 'a' && !data.fieldA) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Field A is required for type A',
      path: ['fieldA'],
    });
  }
});
```

## FastAPI Response Models

### Single Item

```python
@router.get("/{id}", response_model=ItemResponse)
async def get_item(id: int) -> ItemResponse:
    ...
```

### List

```python
@router.get("", response_model=ItemListResponse)
async def list_items() -> ItemListResponse:
    ...
```

### Create (201)

```python
@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(request: ItemCreate) -> ItemResponse:
    ...
```

### No Content (204)

```python
@router.delete("/{id}", status_code=204)
async def delete_item(id: int) -> None:
    ...
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Frontend receives `snake_case` | Schema inherits `BaseModel` | Change to `CamelModel` |
| `undefined` in frontend | Field is `null` in backend | Use `Optional[T] = None` |
| Type mismatch | Python/TS types don't match | Verify type mapping |
| Validation fails | Zod schema doesn't match backend | Update Zod schema |
| Date parsing error | Wrong datetime format | Use `datetime` type in schema |

## Commands

### Generate TypeScript Types (Conceptual)

Currently manual process. For each new Pydantic schema:

1. Create matching TypeScript interface
2. Map field names: `snake_case` → `camelCase`
3. Map types: Python types → TypeScript types
4. Create Zod schema if needed for forms

### Validate Schema Output

```python
# In Python REPL or test
from api.schemas.user_schemas import UserResponse
from datetime import datetime, timezone

user = UserResponse(
    id="123",
    username="john",
    full_name="John Doe",
    is_active=True,
    is_super_admin=False,
    created_at=datetime.now(timezone.utc),
    updated_at=None,
)

# Check JSON output
import json
print(json.dumps(user.model_dump(by_alias=True), indent=2))
# Should output camelCase keys
```

## Best Practices

1. **Always use CamelModel** for all schemas
2. **Create TypeScript types** for every schema
3. **Use Zod** for form validation
4. **Match constraints** between backend and frontend
5. **Test JSON output** before deploying
6. **Document bilingual fields** clearly
