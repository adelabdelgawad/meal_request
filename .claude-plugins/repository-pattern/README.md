# Repository Pattern Plugin

Enforces proper separation of concerns between routers, services, and repositories.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Router (api/v1/)                    │
│  - HTTP concerns (request/response)                      │
│  - Parameter validation                                  │
│  - Call service methods                                  │
│  - Return response models                                │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Service (api/services/)                │
│  - Business logic                                        │
│  - Orchestrate repositories                              │
│  - Permission checks                                     │
│  - Audit logging                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│               Repository (api/repositories/)             │
│  - Database operations ONLY                              │
│  - CRUD methods                                          │
│  - Query building                                        │
│  - NO business logic                                     │
└─────────────────────────────────────────────────────────┘
```

## What It Checks

### Router Violations
- Direct database operations (`select()`, `session.execute()`)
- Direct session manipulation (`session.add()`, `session.commit()`)
- Excessive business logic (many conditionals)

### Service Violations
- Route decorators (services shouldn't define routes)
- Raw SQL execution (should use repository)

### Repository Violations
- HTTPException (use domain exceptions)
- Service imports (circular dependency)
- HTTP calls (external calls belong in services)
- Permission checks (belong in services)

## Correct Pattern

```python
# Router (thin)
@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreate,
    session: AsyncSession = Depends(get_session),
    current_user: Account = Depends(get_current_super_admin),
):
    return await user_service.create_user(
        session, request, created_by_id=str(current_user.id)
    )

# Service (business logic)
class UserService:
    async def create_user(
        self, session: AsyncSession, data: UserCreate, created_by_id: str
    ) -> User:
        # Validation
        existing = await self._repo.get_by_username(session, data.username)
        if existing:
            raise HTTPException(status_code=409, detail="Username exists")

        # Create user
        user = await self._repo.create(session, User(**data.model_dump()))

        # Audit log
        await self._log_service.log_create(session, user, created_by_id)

        return user

# Repository (data access only)
class UserRepository:
    async def get_by_username(
        self, session: AsyncSession, username: str
    ) -> User | None:
        query = select(User).where(User.username == username)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, user: User) -> User:
        session.add(user)
        await session.flush()
        return user
```

## Hook Behavior

- **Type:** PostToolUse (advisory)
- **Trigger:** Write or Edit to router, service, or repository files
- **Action:** Prints warning message, does not block
