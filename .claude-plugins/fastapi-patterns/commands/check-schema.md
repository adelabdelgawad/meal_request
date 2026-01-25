---
description: Check a specific schema file for CamelModel compliance
---

# Check Schema

Validate that a Pydantic schema file follows the CamelModel pattern.

## Instructions

When the user wants to check a schema file, read the file and verify:

1. **CamelModel Inheritance**: All schema classes inherit from `CamelModel`, not `BaseModel`
2. **No Manual Aliases**: No `alias_generator` or `Field(alias=...)` for camelCase
3. **Proper Config**: Has `model_config = ConfigDict(from_attributes=True)`
4. **Field Naming**: Uses `snake_case` for field names

## Validation Steps

1. Read the specified schema file
2. Find all class definitions
3. For each class that looks like a schema (ends with Create, Update, Response, etc.):
   - Check if it inherits from `CamelModel` or another schema that does
   - Report any classes inheriting from `BaseModel` directly
4. Check for anti-patterns:
   - `alias_generator = to_camel` (should be inherited from CamelModel)
   - `Field(alias="camelCase")` (not needed with CamelModel)

## Example Check

For file `src/backend/api/schemas/users.py`:

```
Checking: src/backend/api/schemas/users.py

Classes Found:
  - UserBase(CamelModel) ..................... OK
  - UserCreate(UserBase) ..................... OK (inherits via UserBase)
  - UserResponse(UserBase) ................... OK
  - LoginRequest(BaseModel) .................. ERROR: Should use CamelModel

Anti-patterns Found:
  - Line 45: alias_generator = to_camel (remove - CamelModel handles this)

Summary: 1 error, 1 warning
```

## Quick Fix

If issues are found, suggest the fix:

```python
# Before (WRONG)
from pydantic import BaseModel

class UserCreate(BaseModel):
    user_name: str = Field(alias="userName")

# After (CORRECT)
from api.schemas._base import CamelModel

class UserCreate(CamelModel):
    user_name: str  # Auto-aliased to "userName" in JSON
```

Report all findings clearly with file locations and line numbers.
