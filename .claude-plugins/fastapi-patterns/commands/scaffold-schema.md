---
description: Generate Pydantic schemas following CamelModel pattern
---

# Scaffold Schema

Generate Pydantic request/response schemas that properly inherit from CamelModel.

## Instructions

When the user wants to create schemas for a resource, create the following file:

### Schema File: `src/backend/api/schemas/{resource}.py`

```python
"""
Pydantic schemas for {Resource}.

CRITICAL: All schemas MUST inherit from CamelModel, NOT BaseModel.
This ensures camelCase JSON keys for frontend compatibility.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import Field, ConfigDict

from api.schemas._base import CamelModel


class {Resource}Base(CamelModel):
    """Base schema with shared fields."""
    name_en: str = Field(..., min_length=1, max_length=128)
    name_ar: Optional[str] = Field(None, max_length=128)
    description_en: Optional[str] = Field(None, max_length=512)
    description_ar: Optional[str] = Field(None, max_length=512)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class {Resource}Create({Resource}Base):
    """Schema for creating a new {resource}.

    Used in POST requests.
    """
    pass


class {Resource}Update(CamelModel):
    """Schema for updating a {resource}.

    All fields optional for partial updates.
    Used in PUT/PATCH requests.
    """
    name_en: Optional[str] = Field(None, min_length=1, max_length=128)
    name_ar: Optional[str] = Field(None, max_length=128)
    description_en: Optional[str] = Field(None, max_length=512)
    description_ar: Optional[str] = Field(None, max_length=512)
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class {Resource}Response({Resource}Base):
    """Schema for {resource} responses.

    Includes all fields plus server-generated ones.
    Used in GET responses.
    """
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class {Resource}ListResponse(CamelModel):
    """Schema for paginated list responses."""
    items: List[{Resource}Response]
    total: int
    page: int
    per_page: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
```

## Key Patterns

### DO:
- Always inherit from `CamelModel` (from `api.schemas._base`)
- Use `snake_case` for Python field names (auto-converted to camelCase in JSON)
- Add `model_config = ConfigDict(from_attributes=True)` for ORM compatibility
- Use `Field()` for validation constraints
- Create separate Create, Update, and Response schemas
- Support bilingual fields with `_en` and `_ar` suffixes

### DON'T:
- Inherit from `BaseModel` directly
- Use `alias_generator` manually
- Use `Field(alias="camelCase")` for camelCase conversion
- Mix snake_case and camelCase in field definitions

## Example JSON Output

Given this schema:
```python
class UserResponse(CamelModel):
    user_id: str
    full_name: str
    is_active: bool
    created_at: datetime
```

The JSON output will be:
```json
{
  "userId": "abc123",
  "fullName": "John Doe",
  "isActive": true,
  "createdAt": "2024-01-15T10:30:00Z"
}
```

The conversion happens automatically via CamelModel's `alias_generator`.
