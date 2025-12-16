# Endpoint Implementation Examples

This document shows how to properly implement endpoints following the single session per request pattern.

## Pattern Summary

Every endpoint should follow this structure:

```python
@router.{method}("{path}", response_model=ResponseModel, status_code=StatusCode)
async def endpoint_name(
    # Input parameters
    path_param: Type = Path(...),
    query_param: Type = Query(default),
    body_param: RequestModel = Body(...),

    # Dependencies - ALWAYS include these in this order:
    # 1. Session (explicit)
    session: AsyncSession = Depends(get_session),

    # 2. Service (depends on session)
    service: ServiceType = Depends(get_service_dependency),
):
    """
    Brief description of what this endpoint does.

    The endpoint automatically:
    - Creates exactly one session for the entire request
    - Uses that session for all database operations
    - Closes the session after the response is sent
    """
    try:
        # Business logic
        result = await service.method(params)
        return result
    except DomainException as e:
        # Exception handlers will convert to HTTP response
        raise
```

## Complete Examples

### 1. Create a New Entity (POST)

**File**: `api/v1/auth.py`

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_session, get_user_service
from api.schemas import UserCreate, UserResponse
from api.services import UserService
from core.exceptions import ConflictError, ValidationError, DatabaseError

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """
    Create a new user account.

    The endpoint:
    - Receives one session for the entire request
    - Passes it to UserService
    - UserService uses it to validate and create user
    - Single transaction ensures data consistency

    Args:
        user_create: User creation data
        session: Database session (injected)
        service: User service (depends on session)

    Returns:
        UserResponse: Created user data

    Raises:
        ConflictError: If username/email already exists
        ValidationError: If data is invalid
        DatabaseError: On database errors
    """
    try:
        user = await service.create_user(
            username=user_create.username,
            password=user_create.hashed_password,
            email=user_create.email,
            full_name=getattr(user_create, "full_name", None),
            title=getattr(user_create, "title", None),
            is_domain_user=user_create.is_domain_user,
        )
        return user
    except (ConflictError, ValidationError, DatabaseError):
        raise
```

### 2. Retrieve a Single Entity (GET)

**File**: `api/v1/auth.py`

```python
@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """
    Get a user by ID.

    The endpoint:
    - Uses single session to fetch user
    - Validates user exists before returning

    Args:
        user_id: User ID
        session: Database session (injected)
        service: User service (depends on session)

    Returns:
        UserResponse: User data

    Raises:
        NotFoundError: If user doesn't exist
    """
    try:
        user = await service.get_user(user_id)
        return user
    except NotFoundError:
        raise
```

### 3. List Entities with Filtering (GET)

**File**: `api/v1/meal_requests.py`

```python
from typing import List, Optional

@router.get(
    "/requests",
    response_model=List[MealRequestResponse],
)
async def list_meal_requests(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    requester_id: Optional[str] = Query(None),
    status_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_session),
    service: MealRequestService = Depends(get_meal_request_service),
):
    """
    List meal requests with pagination and filtering.

    The endpoint:
    - Accepts filter parameters
    - Uses single session for pagination query
    - Returns paginated results

    Args:
        page: Page number (1-indexed)
        per_page: Items per page
        requester_id: Filter by requester
        status_id: Filter by status
        session: Database session (injected)
        service: Meal request service (depends on session)

    Returns:
        List[MealRequestResponse]: Paginated meal requests
    """
    requests, total = await service.list_requests(
        page=page,
        per_page=per_page,
        requester_id=requester_id,
        status_id=status_id,
    )
    return requests
```

### 4. Update an Entity (PUT)

**File**: `api/v1/auth.py`

```python
@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """
    Update an existing user.

    The endpoint:
    - Fetches user with single session
    - Validates user exists
    - Updates user data
    - All in one transaction

    Args:
        user_id: User ID to update
        user_update: Updated user data
        session: Database session (injected)
        service: User service (depends on session)

    Returns:
        UserResponse: Updated user data

    Raises:
        NotFoundError: If user doesn't exist
        ConflictError: If username/email conflict
        ValidationError: If data is invalid
    """
    try:
        user = await service.update_user(
            user_id=user_id,
            username=getattr(user_update, "username", None),
            email=getattr(user_update, "email", None),
            full_name=getattr(user_update, "full_name", None),
        )
        return user
    except (NotFoundError, ConflictError, ValidationError, DatabaseError):
        raise
```

### 5. Delete an Entity (DELETE)

**File**: `api/v1/auth.py`

```python
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    """
    Delete a user account.

    The endpoint:
    - Fetches user to verify exists
    - Deletes user (typically soft delete)
    - Single transaction ensures consistency

    Args:
        user_id: User ID to delete
        session: Database session (injected)
        service: User service (depends on session)

    Raises:
        NotFoundError: If user doesn't exist
    """
    try:
        await service.delete_user(user_id)
    except NotFoundError:
        raise
```

### 6. Complex Operation with Multiple Services

**File**: `api/v1/meal_requests.py`

```python
@router.post(
    "/requests",
    response_model=MealRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_meal_request(
    request_data: MealRequestCreate,
    session: AsyncSession = Depends(get_session),
    meal_service: MealRequestService = Depends(get_meal_request_service),
    user_service: UserService = Depends(get_user_service),
    meal_type_service: MealTypeService = Depends(get_meal_type_service),
):
    """
    Create a meal request with validation of related entities.

    The endpoint:
    - Validates user exists with meal_service
    - Validates meal type exists with meal_type_service
    - Creates meal request with meal_service
    - ALL use the SAME session for atomicity

    Args:
        request_data: Meal request creation data
        session: Database session (injected)
        meal_service: Meal service (depends on session)
        user_service: User service (depends on session)
        meal_type_service: Meal type service (depends on session)

    Returns:
        MealRequestResponse: Created meal request

    Raises:
        NotFoundError: If user or meal type doesn't exist
        ValidationError: If data is invalid
        DatabaseError: On database errors
    """
    try:
        # Validate user exists
        user = await user_service.get_user(request_data.requester_id)
        if not user:
            raise NotFoundError(entity="User", identifier=request_data.requester_id)

        # Validate meal type exists
        meal_type = await meal_type_service.get_meal_type(request_data.meal_type_id)
        if not meal_type:
            raise NotFoundError(entity="MealType", identifier=request_data.meal_type_id)

        # Create meal request (uses same session)
        meal_request = await meal_service.create_request(
            requester_id=request_data.requester_id,
            meal_type_id=request_data.meal_type_id,
            notes=getattr(request_data, "notes", None),
        )

        return meal_request

    except (NotFoundError, ValidationError, DatabaseError):
        raise
```

### 7. Batch Operation

**File**: `api/v1/employees.py`

```python
@router.post(
    "/employees/bulk",
    response_model=List[EmployeeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_employees_bulk(
    employees_data: List[EmployeeCreate],
    session: AsyncSession = Depends(get_session),
    service: EmployeeService = Depends(get_employee_service),
):
    """
    Create multiple employees in a single transaction.

    The endpoint:
    - Creates multiple employees
    - Single session ensures atomicity
    - If any creation fails, entire batch fails

    Args:
        employees_data: List of employee creation data
        session: Database session (injected, shared for all creates)
        service: Employee service (depends on session)

    Returns:
        List[EmployeeResponse]: Created employees

    Raises:
        ConflictError: If any employee ID already exists
        ValidationError: If data is invalid
    """
    try:
        employees = []
        for emp_data in employees_data:
            emp = await service.create_employee(
                employee_code=emp_data.employee_code,
                first_name=emp_data.first_name,
                last_name=emp_data.last_name,
                email=emp_data.email,
            )
            employees.append(emp)

        return employees

    except (ConflictError, ValidationError, DatabaseError):
        raise
```

## Key Points to Remember

1. **Always include `session: AsyncSession = Depends(get_session)`**
   - Makes session dependency explicit
   - Ensures FastAPI resolves session first
   - Required for single-session-per-request guarantee

2. **Always include service dependency**
   - Service must depend on `get_session`
   - Services will use cached session from step 1
   - Multiple services in same endpoint use same session

3. **Exception handling**
   - Catch domain exceptions
   - Let exception handlers convert to HTTP responses
   - Don't catch and re-raise unnecessarily

4. **Service method calls**
   - Services handle all repository interaction
   - Don't call repositories directly from endpoint
   - Services abstract database details

5. **Response models**
   - Use Pydantic models for validation
   - Ensures type-safe responses
   - Automatic OpenAPI documentation

## Anti-Patterns to Avoid

### ❌ Don't: Omit session dependency

```python
# WRONG - Session dependency not explicit
@router.post("/users")
async def create_user(
    user_create: UserCreate,
    service: UserService = Depends(get_user_service),  # No session!
):
    pass
```

### ❌ Don't: Create new service without session

```python
# WRONG - Service created without session dependency
@router.post("/users")
async def create_user(
    user_create: UserCreate,
):
    service = UserService()  # Creates service with no session!
    pass
```

### ❌ Don't: Mix dependency types

```python
# WRONG - Explicit session but no service dependency
@router.post("/users")
async def create_user(
    user_create: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)  # Manual creation, not dependency!
    pass
```

## Testing Endpoints

```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_create_user():
    """Test user creation uses single session."""
    response = client.post(
        "/api/v1/auth/users",
        json={
            "username": "testuser",
            "hashed_password": "hashed_pw",
            "email": "test@example.com",
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
```

## Summary

Following these patterns ensures:
- ✓ Exactly one session per HTTP request
- ✓ All database operations in single transaction
- ✓ Proper resource cleanup
- ✓ Clear, maintainable code
- ✓ Easy to test and debug
