---
description: Generate a new FastAPI router following established patterns
---

# Scaffold Router

Generate a new FastAPI router with all the proper patterns already in place.

## Instructions

When the user wants to create a new router, gather these details:
1. **Resource name** (e.g., "products", "orders")
2. **Whether it needs authentication** (default: yes)
3. **CRUD operations needed** (create, read, list, update, delete)

Then create the following files following the established patterns:

### 1. Router File: `src/backend/api/v1/router_{resource}.py`

```python
"""
Router for {Resource} management.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from api.deps import get_session, require_admin
from api.services.{resource}_service import {Resource}Service
from api.schemas.{resource} import (
    {Resource}Create,
    {Resource}Update,
    {Resource}Response,
)

router = APIRouter(prefix="/{resources}", tags=["{resources}"])


@router.post("", response_model={Resource}Response, status_code=status.HTTP_201_CREATED)
async def create_{resource}(
    data: {Resource}Create,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Create a new {resource}."""
    service = {Resource}Service()
    return await service.create(session, data)


@router.get("/{{{resource}_id}}", response_model={Resource}Response)
async def get_{resource}(
    {resource}_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get {resource} by ID."""
    service = {Resource}Service()
    return await service.get_by_id(session, {resource}_id)


@router.get("", response_model=List[{Resource}Response])
async def list_{resources}(
    page: int = 1,
    per_page: int = 25,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_session),
):
    """List {resources} with pagination."""
    service = {Resource}Service()
    items, _ = await service.list(session, page=page, per_page=per_page, is_active=is_active)
    return items


@router.put("/{{{resource}_id}}", response_model={Resource}Response)
async def update_{resource}(
    {resource}_id: str,
    data: {Resource}Update,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Update {resource}."""
    service = {Resource}Service()
    return await service.update(session, {resource}_id, data)


@router.delete("/{{{resource}_id}}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{resource}(
    {resource}_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Delete {resource}."""
    service = {Resource}Service()
    await service.delete(session, {resource}_id)
```

### 2. Also create corresponding:
- Schema file: `src/backend/api/schemas/{resource}.py`
- Service file: `src/backend/api/services/{resource}_service.py`
- Repository file: `src/backend/api/repositories/{resource}_repository.py`

### 3. Register router in `app.py`:
```python
from api.v1.router_{resource} import router as {resource}_router
app.include_router({resource}_router, prefix="/api/v1")
```

## Key Patterns to Follow

1. Use `Depends(get_session)` for database access
2. Use `Depends(require_admin)` or appropriate auth dependency
3. Return proper status codes (201 for create, 204 for delete)
4. Use response_model for automatic serialization
5. Instantiate service in endpoint, don't inject
6. Keep endpoints thin - delegate to service layer
