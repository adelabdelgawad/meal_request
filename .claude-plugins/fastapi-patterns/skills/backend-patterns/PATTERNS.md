# FastAPI Backend Implementation Patterns

Detailed patterns for implementing FastAPI backend features.

## 1. CamelModel Schema Pattern (MANDATORY)

### The Base Class

```python
# api/schemas/_base.py
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that converts snake_case to camelCase in JSON.

    ALL schemas in this project MUST inherit from this class.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Accept both snake_case and camelCase input
        from_attributes=True,   # Allow ORM model conversion
        serialize_by_alias=True,  # Output as camelCase
    )

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override to ensure UTC datetime formatting."""
        data = super().model_dump(**kwargs)
        return self._convert_datetimes(data)

    def _convert_datetimes(self, data: dict) -> dict:
        """Convert datetimes to ISO format with Z suffix."""
        for key, value in data.items():
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                data[key] = value.strftime("%Y-%m-%dT%H:%M:%SZ")
            elif isinstance(value, dict):
                data[key] = self._convert_datetimes(value)
        return data
```

### Schema Organization

```python
# api/schemas/{feature}.py

# 1. Base schema with shared fields
class ProductBase(CamelModel):
    name_en: str = Field(..., min_length=1, max_length=128)
    name_ar: Optional[str] = Field(None, max_length=128)
    price: Decimal = Field(..., ge=0)
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)

# 2. Create schema (for POST)
class ProductCreate(ProductBase):
    category_id: int
    # May have additional required fields

# 3. Update schema (for PUT/PATCH) - all optional
class ProductUpdate(CamelModel):
    name_en: Optional[str] = Field(None, min_length=1, max_length=128)
    name_ar: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)

# 4. Response schema (for GET)
class ProductResponse(ProductBase):
    id: str
    category_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# 5. List response with pagination metadata
class ProductListResponse(CamelModel):
    items: List[ProductResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    active_count: int
    inactive_count: int
```

### JSON Transformation

| Python Field | JSON Key |
|--------------|----------|
| `user_id` | `userId` |
| `is_active` | `isActive` |
| `created_at` | `createdAt` |
| `full_name` | `fullName` |
| `category_id` | `categoryId` |

---

## 2. Router Implementation Pattern

### Standard CRUD Router

```python
"""Router for Product management."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from api.deps import get_session, require_admin, get_current_user
from api.services.product_service import ProductService
from api.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)

router = APIRouter(prefix="/products", tags=["products"])


# CREATE
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
)
async def create_product(
    data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_admin),
):
    """Create a new product.

    Requires admin role.
    """
    service = ProductService()
    product = await service.create(session, data, created_by=current_user["user_id"])
    return product


# READ ONE
@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a single product by ID."""
    service = ProductService()
    return await service.get_by_id(session, product_id)


# READ LIST
@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
)
async def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name fields"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    session: AsyncSession = Depends(get_session),
):
    """List products with pagination and filtering."""
    service = ProductService()
    items, total = await service.list(
        session,
        page=page,
        per_page=per_page,
        is_active=is_active,
        search=search,
        category_id=category_id,
    )

    total_pages = (total + per_page - 1) // per_page
    active_count = len([i for i in items if i.is_active])

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        active_count=active_count,
        inactive_count=len(items) - active_count,
    )


# UPDATE
@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Update an existing product.

    Requires admin role.
    """
    service = ProductService()
    return await service.update(session, product_id, data)


# DELETE
@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product",
)
async def delete_product(
    product_id: str,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Delete a product.

    Requires admin role.
    """
    service = ProductService()
    await service.delete(session, product_id)


# BULK STATUS UPDATE
@router.put(
    "/status",
    response_model=List[ProductResponse],
    summary="Bulk update product status",
)
async def bulk_update_status(
    product_ids: List[str],
    is_active: bool,
    session: AsyncSession = Depends(get_session),
    _: dict = Depends(require_admin),
):
    """Bulk update status for multiple products."""
    service = ProductService()
    return await service.bulk_update_status(session, product_ids, is_active)
```

### Router Registration

```python
# app.py
from api.v1.router_products import router as products_router

app.include_router(products_router, prefix="/api/v1")
```

---

## 3. Service Layer Pattern

### Service Structure

```python
"""Service for Product management."""

from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from api.repositories.product_repository import ProductRepository
from api.repositories.category_repository import CategoryRepository
from api.schemas.product import ProductCreate, ProductUpdate
from core.exceptions import NotFoundError, ConflictError, ValidationError
from db.models import Product


class ProductService:
    """Business logic for products."""

    def __init__(self):
        """Initialize with repositories.

        NOTE: Session is NOT stored - passed to each method.
        """
        self._repo = ProductRepository()
        self._category_repo = CategoryRepository()

    async def create(
        self,
        session: AsyncSession,
        data: ProductCreate,
        created_by: Optional[str] = None,
    ) -> Product:
        """Create a new product.

        Workflow:
        1. Validate business rules
        2. Check constraints (unique, foreign keys)
        3. Create entity
        4. Persist via repository
        5. Post-creation hooks
        """
        # 1. Validate business rules
        errors = []
        if data.price < 0:
            errors.append({"field": "price", "message": "Price must be non-negative"})
        if errors:
            raise ValidationError(errors=errors)

        # 2. Check foreign key exists
        category = await self._category_repo.get_by_id(session, data.category_id)
        if not category:
            raise NotFoundError(entity="Category", identifier=data.category_id)

        # 3. Check unique constraint
        existing = await self._repo.get_by_name(session, data.name_en)
        if existing:
            raise ConflictError(
                entity="Product",
                field="name_en",
                value=data.name_en,
            )

        # 4. Create entity
        product = Product(
            name_en=data.name_en.strip(),
            name_ar=data.name_ar.strip() if data.name_ar else None,
            price=data.price,
            category_id=data.category_id,
            is_active=data.is_active,
            created_by=created_by,
        )

        # 5. Persist
        return await self._repo.create(session, product)

    async def get_by_id(self, session: AsyncSession, product_id: str) -> Product:
        """Get product by ID or raise NotFoundError."""
        product = await self._repo.get_by_id(session, product_id)
        if not product:
            raise NotFoundError(entity="Product", identifier=product_id)
        return product

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        **filters,
    ) -> Tuple[List[Product], int]:
        """List products with pagination."""
        return await self._repo.list(session, page=page, per_page=per_page, **filters)

    async def update(
        self,
        session: AsyncSession,
        product_id: str,
        data: ProductUpdate,
    ) -> Product:
        """Update product."""
        # Ensure exists
        product = await self.get_by_id(session, product_id)

        # Build update dict
        updates = {}
        if data.name_en is not None:
            # Check uniqueness
            existing = await self._repo.get_by_name(session, data.name_en)
            if existing and str(existing.id) != product_id:
                raise ConflictError(
                    entity="Product",
                    field="name_en",
                    value=data.name_en,
                )
            updates["name_en"] = data.name_en.strip()

        if data.name_ar is not None:
            updates["name_ar"] = data.name_ar.strip() if data.name_ar else None
        if data.price is not None:
            updates["price"] = data.price
        if data.is_active is not None:
            updates["is_active"] = data.is_active
        if data.category_id is not None:
            # Verify category exists
            category = await self._category_repo.get_by_id(session, data.category_id)
            if not category:
                raise NotFoundError(entity="Category", identifier=data.category_id)
            updates["category_id"] = data.category_id

        if not updates:
            return product

        return await self._repo.update(session, product_id, updates)

    async def delete(self, session: AsyncSession, product_id: str) -> bool:
        """Delete product."""
        await self.get_by_id(session, product_id)  # Ensure exists
        return await self._repo.delete(session, product_id)

    async def bulk_update_status(
        self,
        session: AsyncSession,
        product_ids: List[str],
        is_active: bool,
    ) -> List[Product]:
        """Bulk update status."""
        return await self._repo.bulk_update_status(session, product_ids, is_active)
```

---

## 4. Repository Layer Pattern

### Repository Structure

```python
"""Repository for Product data access."""

from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.exceptions import ConflictError, DatabaseError
from core.pagination import calculate_offset
from db.models import Product, Category


class ProductRepository:
    """Data access for products."""

    async def create(self, session: AsyncSession, entity: Product) -> Product:
        """Create product."""
        try:
            session.add(entity)
            await session.flush()
            await session.refresh(entity, ["category"])  # Load relationship
            return entity
        except IntegrityError as e:
            await session.rollback()
            if "duplicate" in str(e.orig).lower():
                raise ConflictError(
                    entity="Product",
                    field="name_en",
                    value=entity.name_en,
                )
            raise DatabaseError(f"Failed to create product: {str(e)}")

    async def get_by_id(
        self,
        session: AsyncSession,
        product_id: str,
    ) -> Optional[Product]:
        """Get by ID with eager-loaded relationships."""
        result = await session.execute(
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.category))
        )
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
    ) -> Optional[Product]:
        """Get by English name."""
        result = await session.execute(
            select(Product).where(Product.name_en == name)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        session: AsyncSession,
        page: int = 1,
        per_page: int = 25,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
    ) -> Tuple[List[Product], int]:
        """List with pagination and filters."""
        stmt = select(Product).options(selectinload(Product.category))

        # Filters
        if is_active is not None:
            stmt = stmt.where(Product.is_active == is_active)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if search:
            term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Product.name_en.ilike(term),
                    Product.name_ar.ilike(term),
                )
            )

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar() or 0

        # Paginate
        offset = calculate_offset(page, per_page)
        stmt = stmt.offset(offset).limit(per_page)
        stmt = stmt.order_by(Product.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all()), total

    async def update(
        self,
        session: AsyncSession,
        product_id: str,
        updates: Dict[str, Any],
    ) -> Product:
        """Update product."""
        product = await self.get_by_id(session, product_id)
        if not product:
            return None

        for key, value in updates.items():
            setattr(product, key, value)

        await session.flush()
        await session.refresh(product, ["category"])
        return product

    async def delete(self, session: AsyncSession, product_id: str) -> bool:
        """Delete product."""
        product = await self.get_by_id(session, product_id)
        if not product:
            return False

        await session.delete(product)
        await session.flush()
        return True

    async def bulk_update_status(
        self,
        session: AsyncSession,
        ids: List[str],
        is_active: bool,
    ) -> List[Product]:
        """Bulk status update."""
        result = await session.execute(
            select(Product)
            .where(Product.id.in_(ids))
            .options(selectinload(Product.category))
        )
        products = list(result.scalars().all())

        for product in products:
            product.is_active = is_active

        await session.flush()
        return products
```

---

## 5. Model Definition Pattern

### SQLAlchemy 2.0 Model

```python
"""SQLAlchemy ORM models."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.maria_database import Base


class Product(Base):
    """Product entity."""

    __tablename__ = "product"

    # Primary key - UUID as CHAR(36) for MySQL
    id: Mapped[str] = mapped_column(
        CHAR(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Bilingual name fields
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Description fields
    description_en: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    description_ar: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Price with precision
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Foreign key
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("category.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    # Audit fields
    created_by: Mapped[Optional[str]] = mapped_column(
        CHAR(36),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="products")

    def get_name(self, locale: str = "en") -> str:
        """Get localized name."""
        if locale == "ar" and self.name_ar:
            return self.name_ar
        return self.name_en
```

### Relationship Patterns

```python
# One-to-Many (Category has many Products)
class Category(Base):
    products: Mapped[List["Product"]] = relationship(back_populates="category")

class Product(Base):
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"))
    category: Mapped["Category"] = relationship(back_populates="products")

# Many-to-Many (User has many Roles via RolePermission)
class User(Base):
    role_permissions: Mapped[List["RolePermission"]] = relationship(back_populates="user")

class Role(Base):
    role_permissions: Mapped[List["RolePermission"]] = relationship(back_populates="role")

class RolePermission(Base):  # Association table
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), primary_key=True)
    user: Mapped["User"] = relationship(back_populates="role_permissions")
    role: Mapped["Role"] = relationship(back_populates="role_permissions")
```

---

## 6. Exception Handling Pattern

### Domain Exceptions

```python
# core/exceptions.py

class DomainException(Exception):
    """Base domain exception."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(DomainException):
    """Entity not found - maps to 404."""
    def __init__(self, entity: str, identifier: Any, message: str = None):
        self.entity = entity
        self.identifier = identifier
        super().__init__(message or f"{entity} '{identifier}' not found")


class ConflictError(DomainException):
    """Unique constraint violation - maps to 409."""
    def __init__(self, entity: str, field: str, value: Any, message: str = None):
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(message or f"{entity} with {field}='{value}' already exists")


class ValidationError(DomainException):
    """Validation failed - maps to 422."""
    def __init__(self, errors: List[Dict[str, Any]], message: str = None):
        self.errors = errors
        super().__init__(message or f"Validation failed: {len(errors)} error(s)")


class AuthenticationError(DomainException):
    """Authentication failed - maps to 401."""
    pass


class AuthorizationError(DomainException):
    """Authorization failed - maps to 403."""
    pass
```

### Exception Handlers

```python
# app.py

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc), "entity": exc.entity},
    )

@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "entity": exc.entity, "field": exc.field},
    )

@app.exception_handler(ValidationError)
async def validation_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "errors": exc.errors},
    )
```

---

## 7. Authentication Pattern

### JWT Token Structure

```python
# Token payload
{
    "user_id": "uuid-string",
    "username": "john.doe",
    "scopes": ["admin", "requester"],  # Permission scopes
    "roles": ["Admin", "Requester"],   # Role names
    "locale": "en",                     # User's preferred locale
    "jti": "unique-token-id",          # For revocation
    "exp": 1234567890,                 # Expiration timestamp
    "type": "access"                   # or "refresh"
}
```

### Dependency Functions

```python
# api/deps.py

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Extract and verify JWT token."""
    token = extract_token(request)
    payload = verify_access_token(token)

    # Check revocation
    if await is_token_revoked(session, payload["jti"]):
        raise HTTPException(401, "Token revoked")

    return payload


async def require_admin(
    payload: dict = Depends(get_current_user),
) -> dict:
    """Require admin scope."""
    if "admin" not in payload.get("scopes", []):
        raise HTTPException(403, "Admin role required")
    return payload


async def require_super_admin(
    payload: dict = Depends(get_current_user),
) -> dict:
    """Require super_admin scope."""
    if "super_admin" not in payload.get("scopes", []):
        raise HTTPException(403, "Super Admin role required")
    return payload
```
