# CamelModel Enforcement Plugin

Enforces that all Pydantic schemas in `api/schemas/` inherit from `CamelModel` instead of `BaseModel` directly.

## Why This Matters

The frontend JavaScript expects camelCase JSON keys (e.g., `fullName`, `isActive`), while Python convention uses snake_case (e.g., `full_name`, `is_active`). The `CamelModel` base class handles this conversion automatically.

**Without CamelModel:**
```json
{"full_name": "John", "is_active": true}  // Frontend parsing fails!
```

**With CamelModel:**
```json
{"fullName": "John", "isActive": true}  // Frontend works correctly
```

## What It Checks

1. **BaseModel inheritance** - Flags classes that inherit from `BaseModel` directly
2. **Manual alias generators** - Flags duplicate alias configuration
3. **Manual Field aliases** - Flags `Field(alias="camelCase")` patterns
4. **Missing imports** - Flags schema files without CamelModel import

## Correct Pattern

```python
from api.schemas._base import CamelModel

class UserResponse(CamelModel):
    user_id: int      # Serializes to "userId"
    full_name: str    # Serializes to "fullName"
    is_active: bool   # Serializes to "isActive"
```

## Incorrect Patterns

```python
# WRONG - Direct BaseModel inheritance
from pydantic import BaseModel

class UserResponse(BaseModel):
    user_id: int  # Will serialize as "user_id"

# WRONG - Manual alias (unnecessary with CamelModel)
from pydantic import Field

class UserResponse(CamelModel):
    user_id: int = Field(alias="userId")  # Unnecessary!
```

## Hook Behavior

- **Type:** PostToolUse (advisory)
- **Trigger:** Write or Edit to `api/schemas/*.py` files
- **Excludes:** `_base.py` (defines CamelModel itself)
- **Action:** Prints warning message, does not block

## Installation

The plugin is automatically loaded when placed in `.claude-plugins/camelmodel-enforcement/`.
