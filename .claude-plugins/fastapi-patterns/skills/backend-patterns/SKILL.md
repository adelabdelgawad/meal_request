---
name: backend-patterns
description: |
  Build FastAPI backend features following established architecture patterns.
  Use when creating routers, services, repositories, schemas, or models.
  Enforces CamelModel for schemas, proper async patterns, and layered architecture.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
---

# FastAPI Backend Development Patterns

## Overview

This skill teaches how to build FastAPI backend features following the established architecture in this codebase. The architecture follows clean architecture principles:

```
Router (API Layer) → Service (Business Logic) → Repository (Data Access) → Model (ORM)
```

**CRITICAL RULES:**
1. All Pydantic schemas MUST inherit from `CamelModel`
2. Services MUST NOT store session as instance variable
3. All database methods MUST be async
4. Use domain exceptions, not HTTPException in services

## When to Use This Skill

Activate when request involves:
- Creating new API endpoints/routers
- Adding Pydantic request/response schemas
- Creating service layer classes
- Adding repository classes
- Defining SQLAlchemy models
- Working with database operations
- Implementing CRUD operations
- Adding authentication/authorization
- Error handling patterns

## Quick Reference

### Project Structure

```
src/backend/
├── api/
│   ├── v1/                    # API routers
│   │   └── router_{feature}.py
│   ├── schemas/               # Pydantic DTOs
│   │   ├── _base.py          # CamelModel base class
│   │   └── {feature}.py
│   ├── services/              # Business logic
│   │   └── {feature}_service.py
│   ├── repositories/          # Data access
│   │   └── {feature}_repository.py
│   └── deps.py               # Dependency injection
├── db/
│   ├── models.py             # SQLAlchemy models
│   └── maria_database.py     # Database connection
├── core/
│   ├── exceptions.py         # Domain exceptions
│   └── pagination.py         # Pagination utilities
└── app.py                    # FastAPI application
```

### File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Router | `router_{feature}.py` | `router_products.py` |
| Schema | `{feature}.py` | `products.py` |
| Service | `{feature}_service.py` | `products_service.py` |
| Repository | `{feature}_repository.py` | `products_repository.py` |

## Core Patterns

### 1. Schema Pattern (CRITICAL)

```python
# ALWAYS inherit from CamelModel, NOT BaseModel
from api.schemas._base import CamelModel

class ProductCreate(CamelModel):
    name_en: str           # Becomes "nameEn" in JSON
    is_active: bool        # Becomes "isActive" in JSON
    category_id: int       # Becomes "categoryId" in JSON

    model_config = ConfigDict(from_attributes=True)
```

**DO NOT:**
```python
# WRONG - Don't use BaseModel directly
from pydantic import BaseModel
class ProductCreate(BaseModel):  # ❌ Wrong!
    pass

# WRONG - Don't use manual aliases
class ProductCreate(CamelModel):
    name: str = Field(alias="name")  # ❌ Unnecessary
```

### 2. Router Pattern

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session, require_admin

router = APIRouter(prefix="/products", tags=["products"])

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Create a new product."""
    service = ProductService()
    return await service.create(session, data)
```

### 3. Service Pattern

```python
class ProductService:
    def __init__(self):
        self._repo = ProductRepository()
        # ❌ DON'T: self._session = session

    async def create(self, session: AsyncSession, data: ProductCreate) -> Product:
        # Validate
        if not data.name_en:
            raise ValidationError(errors=[{"field": "name_en", "message": "Required"}])

        # Check conflicts
        existing = await self._repo.get_by_name(session, data.name_en)
        if existing:
            raise ConflictError(entity="Product", field="name_en", value=data.name_en)

        # Create
        entity = Product(name_en=data.name_en, ...)
        return await self._repo.create(session, entity)
```

### 4. Repository Pattern

```python
class ProductRepository:
    async def create(self, session: AsyncSession, entity: Product) -> Product:
        session.add(entity)
        await session.flush()  # NOT commit()!
        await session.refresh(entity)
        return entity

    async def get_by_id(self, session: AsyncSession, id: str) -> Optional[Product]:
        result = await session.execute(
            select(Product).where(Product.id == id)
        )
        return result.scalar_one_or_none()
```

### 5. Model Pattern

```python
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.maria_database import Base

class Product(Base):
    __tablename__ = "product"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

## Exception Hierarchy

| Exception | HTTP Status | Usage |
|-----------|-------------|-------|
| `NotFoundError` | 404 | Entity not found |
| `ConflictError` | 409 | Unique constraint violation |
| `ValidationError` | 422 | Input validation failed |
| `AuthenticationError` | 401 | Invalid credentials |
| `AuthorizationError` | 403 | Permission denied |
| `DatabaseError` | 500 | Database operation failed |

```python
# In service
raise NotFoundError(entity="Product", identifier=product_id)
raise ConflictError(entity="Product", field="name_en", value=name)
raise ValidationError(errors=[{"field": "price", "message": "Must be positive"}])
```

## Dependency Injection

```python
# Session dependency (use in every endpoint)
session: AsyncSession = Depends(get_session)

# Authentication dependencies
current_user: dict = Depends(get_current_user)
_: dict = Depends(require_admin)
_: dict = Depends(require_super_admin)
```

## Validation Checklist

Before completing backend work:

- [ ] Schemas inherit from `CamelModel`
- [ ] Schemas have `model_config = ConfigDict(from_attributes=True)`
- [ ] Services don't store session as instance variable
- [ ] All repository methods are async
- [ ] Using `flush()` not `commit()` in repositories
- [ ] Domain exceptions used (not HTTPException in services)
- [ ] Router uses proper dependency injection
- [ ] Models use `Mapped` type hints

## Additional Resources

- [PATTERNS.md](PATTERNS.md) - Detailed implementation patterns
- [REFERENCE.md](REFERENCE.md) - Complete API reference
- [EXAMPLES.md](EXAMPLES.md) - Working code examples

## Trigger Phrases

- "create router", "add endpoint", "API route"
- "pydantic schema", "request model", "response model"
- "service layer", "business logic"
- "repository", "data access", "CRUD"
- "SQLAlchemy model", "database model"
- "CamelModel", "camelCase", "snake_case"
- "async", "await", "session"
- "validation", "error handling"
