# Session Management Plugin

Checks for proper database session lifecycle management in FastAPI endpoints and services.

## Why This Matters

Improper session management causes:
- **Session leaks** - Sessions not closed properly
- **Transaction issues** - Multiple sessions for one request
- **Connection exhaustion** - Pool depleted from leaks
- **Data inconsistency** - Partial commits across sessions

## Session Flow

```
Request arrives
    ↓
Middleware creates session via Depends(get_session)
    ↓
Router receives session as parameter
    ↓
Router passes session to service methods
    ↓
Service passes session to repository methods
    ↓
Response sent
    ↓
Middleware closes session (automatic with context manager)
```

## What It Checks

### In Routers
1. **Missing session dependency** - Endpoints that need sessions but don't declare them
2. **Direct commits** - Routers shouldn't commit sessions directly

### In Services
1. **Session creation** - Services shouldn't create their own sessions
2. **Stored sessions** - Sessions shouldn't be instance variables
3. **Missing awaits** - Async operations must be awaited

## Correct Pattern

### Router

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.maria_database import get_session

router = APIRouter()

@router.get("/items")
async def get_items(
    session: AsyncSession = Depends(get_session),  # ✅ Via dependency
):
    return await item_service.get_items(session)  # ✅ Pass to service

@router.post("/items")
async def create_item(
    data: ItemCreate,
    session: AsyncSession = Depends(get_session),
):
    result = await item_service.create_item(session, data)
    # ❌ DON'T commit here - let service handle it
    return result
```

### Service

```python
class ItemService:
    def __init__(self):
        self._repo = ItemRepository()
        # ❌ DON'T: self._session = None

    async def get_items(
        self,
        session: AsyncSession,  # ✅ Receive as parameter
    ):
        return await self._repo.list(session)

    async def create_item(
        self,
        session: AsyncSession,
        data: ItemCreate,
    ):
        item = await self._repo.create(session, Item(**data.model_dump()))
        await session.commit()  # ✅ Service handles commit
        return item
```

### Repository

```python
class ItemRepository:
    async def list(
        self,
        session: AsyncSession,  # ✅ Receive as parameter
    ):
        query = select(Item)
        result = await session.execute(query)
        return result.scalars().all()

    async def create(
        self,
        session: AsyncSession,
        item: Item,
    ):
        session.add(item)
        await session.flush()  # ✅ Flush, don't commit
        return item
```

## Anti-Patterns

### Creating Sessions in Services

```python
# ❌ WRONG
class BadService:
    async def get_items(self):
        async with DatabaseSessionLocal() as session:
            return await self._repo.list(session)
        # Creates new session per call!
```

### Storing Sessions as Instance Variables

```python
# ❌ WRONG
class BadService:
    def __init__(self, session: AsyncSession):
        self._session = session  # Stored reference!

    async def get_items(self):
        return await self._repo.list(self._session)
```

### Direct Commits in Router

```python
# ❌ WRONG
@router.post("/items")
async def create_item(session: AsyncSession = Depends(get_session)):
    item = Item(name="test")
    session.add(item)
    await session.commit()  # Router handling transaction!
    return item
```

## Hook Behavior

- **Type:** PostToolUse (advisory)
- **Trigger:** Write or Edit to router or service files
- **Action:** Prints warning message, does not block
