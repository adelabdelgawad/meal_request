# FastAPI Backend API Reference

Complete reference for all components in the FastAPI backend architecture.

## CamelModel Base Class

**Path:** `api/schemas/_base.py`

### Configuration

| Option | Value | Purpose |
|--------|-------|---------|
| `alias_generator` | `to_camel` | Converts `snake_case` → `camelCase` |
| `populate_by_name` | `True` | Accept both snake_case and camelCase input |
| `from_attributes` | `True` | Enable ORM model conversion |
| `serialize_by_alias` | `True` | Output JSON with camelCase keys |

### Methods

```python
def model_dump(self, **kwargs) -> dict:
    """Serialize with UTC datetime formatting."""

def _convert_datetimes(self, data: dict) -> dict:
    """Convert datetimes to ISO format with Z suffix."""
```

---

## Domain Exceptions

**Path:** `core/exceptions.py`

### NotFoundError

```python
class NotFoundError(DomainException):
    """404 Not Found"""

    def __init__(
        self,
        entity: str,           # Entity type (e.g., "Product")
        identifier: Any,       # ID or key that wasn't found
        message: str = None,   # Custom message (optional)
    )

# Usage
raise NotFoundError(entity="Product", identifier="abc-123")
# Message: "Product 'abc-123' not found"
```

### ConflictError

```python
class ConflictError(DomainException):
    """409 Conflict"""

    def __init__(
        self,
        entity: str,           # Entity type
        field: str,            # Field that has conflict
        value: Any,            # Conflicting value
        message: str = None,
    )

# Usage
raise ConflictError(entity="Product", field="name_en", value="Widget")
# Message: "Product with name_en='Widget' already exists"
```

### ValidationError

```python
class ValidationError(DomainException):
    """422 Unprocessable Entity"""

    def __init__(
        self,
        errors: List[Dict[str, Any]],  # List of field errors
        message: str = None,
    )

# Usage
raise ValidationError(errors=[
    {"field": "price", "message": "Must be positive"},
    {"field": "name_en", "message": "Required"},
])
```

### AuthenticationError

```python
class AuthenticationError(DomainException):
    """401 Unauthorized"""

    def __init__(self, message: str = "Authentication failed")
```

### AuthorizationError

```python
class AuthorizationError(DomainException):
    """403 Forbidden"""

    def __init__(self, message: str = "Permission denied")
```

---

## Dependency Functions

**Path:** `api/deps.py`

### get_session

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for request.

    Usage in router:
        session: AsyncSession = Depends(get_session)

    The session:
    - Auto-commits on successful response
    - Auto-rollbacks on exception
    - Auto-closes after request
    """
```

### get_current_user

```python
async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Extract and verify JWT token.

    Returns dict with:
    - user_id: str
    - username: str
    - scopes: List[str]
    - roles: List[str]
    - locale: str
    - jti: str

    Raises:
    - HTTPException(401) if token invalid/expired/revoked
    """
```

### require_admin

```python
async def require_admin(
    payload: dict = Depends(get_current_user),
) -> dict:
    """Require admin or super_admin scope.

    Usage:
        _: dict = Depends(require_admin)

    Raises:
    - HTTPException(403) if user lacks admin scope
    """
```

### require_super_admin

```python
async def require_super_admin(
    payload: dict = Depends(get_current_user),
) -> dict:
    """Require super_admin scope.

    Raises:
    - HTTPException(403) if user lacks super_admin scope
    """
```

### get_locale

```python
async def get_locale(
    request: Request,
    lang: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
) -> str:
    """Resolve user's locale.

    Priority:
    1. ?lang= query parameter
    2. JWT payload locale
    3. Accept-Language header
    4. User's preferred_locale (DB)
    5. Default: "en"

    Returns: "en" or "ar"
    """
```

---

## Pagination Utilities

**Path:** `core/pagination.py`

### calculate_offset

```python
def calculate_offset(page: int, page_size: int) -> int:
    """Calculate SQL OFFSET from page number.

    Args:
        page: 1-indexed page number
        page_size: Items per page

    Returns:
        Offset for SQL query

    Example:
        calculate_offset(1, 25)  # Returns 0
        calculate_offset(2, 25)  # Returns 25
        calculate_offset(3, 10)  # Returns 20
    """
```

### calculate_pagination_metadata

```python
def calculate_pagination_metadata(
    total_count: int,
    page: int,
    page_size: int,
) -> PaginationMetadata:
    """Generate pagination metadata.

    Returns:
        PaginationMetadata with:
        - total_count: int
        - page: int
        - page_size: int
        - total_pages: int
        - has_next: bool
        - has_previous: bool
    """
```

---

## HTTP Client (clientApi / serverApi)

**Path:** `lib/http/axios-client.ts` (frontend) / `lib/http/axios-server.py` (backend)

### serverApi (Backend)

```python
# For server-side requests (in server actions)
from lib.http.axios_server import serverApi

result = await serverApi.get("/endpoint", params={"key": "value"}, useVersioning=True)
# Calls: GET /api/v1/endpoint?key=value

if result.ok:
    data = result.data
else:
    error = result.error
```

### Methods

| Method | Signature |
|--------|-----------|
| `get` | `get(url, params=None, useVersioning=True)` |
| `post` | `post(url, data, useVersioning=True)` |
| `put` | `put(url, data, useVersioning=True)` |
| `patch` | `patch(url, data, useVersioning=True)` |
| `delete` | `delete(url, useVersioning=True)` |

### Response Structure

```python
@dataclass
class ApiResult:
    ok: bool              # True if 2xx status
    status: int           # HTTP status code
    data: Optional[T]     # Response data (if ok)
    error: Optional[str]  # Error message (if not ok)
```

---

## SQLAlchemy Column Types

### Common Types

| Python Type | SQLAlchemy Type | MySQL Type |
|-------------|-----------------|------------|
| `str` | `String(n)` | `VARCHAR(n)` |
| `int` | `Integer` | `INT` |
| `bool` | `Boolean` | `TINYINT(1)` |
| `datetime` | `DateTime(timezone=True)` | `DATETIME` |
| `Decimal` | `Numeric(10, 2)` | `DECIMAL(10,2)` |
| `UUID` | `CHAR(36)` | `CHAR(36)` |
| `Optional[str]` | `String(n), nullable=True` | `VARCHAR(n) NULL` |

### UUID Pattern

```python
from sqlalchemy.dialects.mysql import CHAR
import uuid

id: Mapped[str] = mapped_column(
    CHAR(36),
    primary_key=True,
    default=lambda: str(uuid.uuid4()),
)
```

### Timestamp Pattern

```python
from sqlalchemy import DateTime, func

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
```

### Foreign Key Pattern

```python
from sqlalchemy import ForeignKey

category_id: Mapped[int] = mapped_column(
    Integer,
    ForeignKey("category.id", ondelete="RESTRICT"),  # or CASCADE, SET NULL
    nullable=False,
)
```

---

## Router Decorators

### HTTP Methods

```python
@router.get(path, response_model=Schema, status_code=200)
@router.post(path, response_model=Schema, status_code=201)
@router.put(path, response_model=Schema, status_code=200)
@router.patch(path, response_model=Schema, status_code=200)
@router.delete(path, status_code=204)
```

### Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `response_model` | `Type[BaseModel]` | Schema for response serialization |
| `status_code` | `int` | HTTP status code |
| `summary` | `str` | Short description for docs |
| `description` | `str` | Detailed description for docs |
| `tags` | `List[str]` | Grouping tags |
| `deprecated` | `bool` | Mark as deprecated |

### Query Parameters

```python
from fastapi import Query

@router.get("/items")
async def list_items(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(25, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, min_length=1, description="Search term"),
    is_active: Optional[bool] = Query(None, description="Filter by status"),
):
```

### Path Parameters

```python
@router.get("/items/{item_id}")
async def get_item(
    item_id: str,  # Automatically extracted from path
):
```

---

## SQLAlchemy Query Patterns

### Select

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Basic select
stmt = select(Product)
result = await session.execute(stmt)
products = result.scalars().all()

# Single item
stmt = select(Product).where(Product.id == id)
result = await session.execute(stmt)
product = result.scalar_one_or_none()

# With relationship eager loading
stmt = select(Product).options(selectinload(Product.category))
```

### Filter

```python
from sqlalchemy import or_, and_

# Equal
stmt = stmt.where(Product.is_active == True)

# In list
stmt = stmt.where(Product.id.in_(ids))

# Like/ILike
stmt = stmt.where(Product.name_en.ilike(f"%{search}%"))

# OR condition
stmt = stmt.where(or_(
    Product.name_en.ilike(term),
    Product.name_ar.ilike(term),
))

# AND condition
stmt = stmt.where(and_(
    Product.is_active == True,
    Product.category_id == category_id,
))
```

### Pagination

```python
from sqlalchemy import func

# Count
count_stmt = select(func.count()).select_from(Product)
total = (await session.execute(count_stmt)).scalar()

# Paginate
stmt = stmt.offset(offset).limit(limit)

# Order
stmt = stmt.order_by(Product.created_at.desc())
```

### Aggregate

```python
from sqlalchemy import func

# Count
stmt = select(func.count()).select_from(Product).where(Product.is_active == True)
active_count = (await session.execute(stmt)).scalar()

# Sum
stmt = select(func.sum(OrderLine.quantity)).where(OrderLine.order_id == order_id)
total_qty = (await session.execute(stmt)).scalar()
```

---

## Field Validation

### Pydantic Field

```python
from pydantic import Field

class ProductCreate(CamelModel):
    # Required with constraints
    name_en: str = Field(..., min_length=1, max_length=128)

    # Optional
    name_ar: Optional[str] = Field(None, max_length=128)

    # Numeric constraints
    price: Decimal = Field(..., ge=0, le=999999.99)
    quantity: int = Field(..., ge=0, le=10000)

    # Pattern validation
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")

    # Description for docs
    is_active: bool = Field(True, description="Whether the product is active")
```

### Custom Validators

```python
from pydantic import model_validator

class DateRangeSchema(CamelModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self
```
