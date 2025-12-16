# Single Session Per Request Data Access Pattern

## Overview

This document describes the data access pattern used in the application to guarantee that **each HTTP request uses exactly one database session**.

## Architecture

```
┌─────────────────────────────────────────────┐
│           HTTP Request Arrives              │
└────────────────────┬────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │    get_session()       │◄─── Creates single AsyncSession
        │   (dependency)         │     per request
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │    Endpoint Handler    │
        │  - Depends(get_session)│
        │  - Service Dependency  │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │    Service Layer       │
        │  __init__(session)     │
        │  Creates Repositories  │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │   Repository Layer     │
        │  Uses Injected Session │
        │  No New Sessions       │
        └────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────────┐
        │   Database Operations  │
        │  Single Transaction    │
        └────────────────────────┘
```

## Dependency Chain

The FastAPI dependency injection system resolves dependencies in order:

```
Endpoint
  ├─ session: AsyncSession = Depends(get_session)
  │  └─ Resolves: get_async_session() → AsyncSession
  │
  └─ service: UserService = Depends(get_user_service)
     └─ Depends(get_session) → AsyncSession (CACHED)
     └─ Creates: UserService(session)
```

**Key Point**: FastAPI caches dependency results within a request. When `get_user_service` depends on `get_session`, FastAPI:
1. Resolves `get_session()` → creates AsyncSession
2. Caches this session instance
3. When `get_user_service` requests the same dependency, provides the cached instance
4. Service receives the same session instance

## Implementation Guidelines

### Endpoint Level

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_session, get_user_service
from api.services import UserService

router = APIRouter()

@router.post("/users")
async def create_user(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),  # ✓ Explicit session dependency
    service: UserService = Depends(get_user_service),  # ✓ Service depends on get_session
):
    """
    Create a new user.

    Guarantees:
    - Single session per request
    - Session used for all database operations in the handler
    - Session automatically closed after response
    """
    user = await service.create_user(
        username=user_create.username,
        password=user_create.password,
    )
    return user
```

### Service Level

```python
from sqlalchemy.ext.asyncio import AsyncSession
from api.repositories.user_repository import UserRepository

class UserService:
    """Service for user management."""

    def __init__(self, session: AsyncSession):
        """Initialize with injected session.

        Args:
            session: AsyncSession from endpoint (required, no default)
        """
        self._session = session
        self._repo = UserRepository(session)  # Pass to repositories

    async def create_user(self, username: str, password: str):
        """Create a new user using the injected session."""
        # All repository calls use the same session
        return await self._repo.create(user_obj)

    async def get_related_data(self, user_id: int):
        """Example: Multiple repository calls use same session."""
        user = await self._repo.get_by_id(user_id)
        role = await self._role_repo.get_by_id(user.role_id)
        # Both calls use the same session instance
        return user, role
```

### Repository Level

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserRepository:
    """Data access layer for users."""

    def __init__(self, session: AsyncSession):
        """Initialize with injected session.

        Args:
            session: AsyncSession from service
        """
        self._session = session  # Use provided session, never create new ones

    async def create(self, user_obj):
        """Create user using injected session."""
        self._session.add(user_obj)
        await self._session.flush()
        return user_obj

    async def get_by_id(self, user_id: int):
        """Get user using injected session."""
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()
```

## Dependency Injection Configuration

All service dependencies in `api/deps.py` follow this pattern:

```python
async def get_user_service(
    session: AsyncSession = Depends(get_session)  # ✓ Required session
) -> UserService:
    """Get UserService with injected session.

    The session dependency must be resolved before creating the service.
    This ensures the service uses the same session instance for all
    repository calls.
    """
    return UserService(session)
```

**Why `Depends(get_session)` instead of `session: AsyncSession = None`?**

- **Before**: `session: AsyncSession = None` created optional implicit dependency
  - FastAPI wouldn't enforce session resolution
  - Could create multiple sessions if not careful
  - Unclear that session is being used

- **After**: `session: AsyncSession = Depends(get_session)` creates explicit dependency
  - FastAPI enforces session resolution order
  - Guarantees same session instance
  - Clear that session is required
  - Compile-time validation

## Endpoint Pattern Examples

### Create Operation (Single Entity)

```python
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),  # Explicit
    service: UserService = Depends(get_user_service),
):
    """Create a new user - single session for all operations."""
    user = await service.create_user(
        username=user_create.username,
        password=user_create.password,
    )
    return user
```

### Read Operation (List with Pagination)

```python
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    per_page: int = 25,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """List users - single session for all operations."""
    users, total = await service.list_users(page=page, per_page=per_page)
    return users
```

### Update Operation (Modify Entity)

```python
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """Update user - single session for validation and update."""
    user = await service.update_user(user_id, **user_update.dict())
    return user
```

### Delete Operation (Remove Entity)

```python
@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """Delete user - single session for validation and deletion."""
    await service.delete_user(user_id)
```

## Multi-Service Transactions

For operations requiring multiple services, ensure all depend on the same session:

```python
@router.post("/meals/request")
async def create_meal_request(
    request_data: MealRequestCreate,
    session: AsyncSession = Depends(get_session),  # Explicit
    meal_service: MealRequestService = Depends(get_meal_request_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Create meal request with user validation.

    Both services use the same session:
    - meal_service._session (for meal operations)
    - user_service._session (for user validation)

    Both reference the same AsyncSession instance.
    """
    # Verify user exists
    user = await user_service.get_user(request_data.requester_id)

    # Create meal request
    meal_request = await meal_service.create_request(
        requester_id=request_data.requester_id,
        meal_type_id=request_data.meal_type_id,
    )

    return meal_request
```

## Best Practices

### DO

✓ **Always depend on `get_session()` explicitly in endpoints**
```python
async def my_endpoint(
    session: AsyncSession = Depends(get_session),
    service: MyService = Depends(get_my_service),
):
    pass
```

✓ **Pass session to services in constructor**
```python
class MyService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = MyRepository(session)
```

✓ **Pass session from service to all repositories**
```python
class MyService:
    def __init__(self, session: AsyncSession):
        self._repo1 = Repository1(session)
        self._repo2 = Repository2(session)
```

✓ **Store session as instance variable in services**
```python
class MyService:
    def __init__(self, session: AsyncSession):
        self._session = session  # Store for future use
```

### DON'T

✗ **Don't create new sessions in repositories**
```python
# ✗ WRONG
class MyRepository:
    async def create(self, obj):
        session = Session()  # Creates new session!
        session.add(obj)
```

✗ **Don't use default parameters for session**
```python
# ✗ WRONG
async def get_user_service(session: AsyncSession = None):
    return UserService(session)
```

✗ **Don't depend on services without depending on get_session**
```python
# ✗ WRONG
async def my_endpoint(service: MyService = Depends(get_my_service)):
    # Session dependency not explicit
    pass
```

✗ **Don't pass different sessions to different repositories in same service**
```python
# ✗ WRONG
class MyService:
    def __init__(self, session: AsyncSession):
        self._repo1 = Repository1(session)
        self._repo2 = Repository2(Session())  # Different session!
```

## Session Lifecycle

```
Request Arrives
    │
    ▼
get_async_session() creates AsyncSession
    │
    ▼
Endpoint depends on get_session() → receives session
    │
    ▼
Service created with session → creates repositories
    │
    ▼
Service methods use session via repositories
    │
    ▼
Repository methods execute queries on session
    │
    ▼
Response sent
    │
    ▼
get_async_session() context manager:
  - Flushes pending changes
  - Closes session
  - Cleans up resources
    │
    ▼
Request Complete
```

## Testing the Pattern

To verify a request uses exactly one session, count session creation calls:

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_single_session_per_request():
    """Verify that an endpoint creates exactly one session."""

    with patch('core.session.DatabaseManager.get_session_maker') as mock_maker:
        # Create mock session
        mock_session = AsyncMock()
        mock_maker.return_value.return_value = mock_session

        # Make request
        response = await client.post("/users", json={"username": "test"})

        # Verify session was created once
        assert mock_session.add.call_count >= 1  # At least one DB operation
        assert mock_session.__aenter__.call_count == 1  # Session opened once
        assert mock_session.__aexit__.call_count == 1  # Session closed once
```

## Summary

The single session per request pattern ensures:

1. **Consistency**: All database operations in a request use the same transaction context
2. **Efficiency**: No unnecessary session creation/cleanup overhead
3. **Safety**: Proper isolation between concurrent requests
4. **Clarity**: Explicit dependencies make code intent clear
5. **Maintainability**: Easy to trace data flow and session lifetime

By following this pattern, the application guarantees atomic operations and predictable behavior across the request lifecycle.
