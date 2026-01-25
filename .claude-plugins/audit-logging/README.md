# Audit Logging Plugin

Checks that service methods include audit logging for mutations on sensitive entities.

## Why This Matters

Audit logging is required for:
- **Compliance** - Track who did what and when
- **Security** - Detect unauthorized changes
- **Debugging** - Trace issues to their source
- **Accountability** - Record of all actions

## Sensitive Entities

The following entities require audit logging:
- `user` - User account changes
- `role` - Role modifications
- `permission` - Permission assignments
- `page_permission` - Page access changes
- `role_permission` - Role assignments

## What It Checks

1. **Mutation methods** - create, update, delete, assign, revoke, toggle
2. **Log service usage** - Checks for `_log_service` calls
3. **Log service import** - Checks for log service initialization

## Correct Pattern

```python
from api.services.log_user_service import LogUserService

class UserService:
    def __init__(self):
        self._repo = UserRepository()
        self._log_service = LogUserService()  # Initialize log service

    async def create_user(
        self,
        session: AsyncSession,
        data: UserCreate,
        created_by_id: str,
    ) -> User:
        # Create user
        user = await self._repo.create(session, User(**data.model_dump()))

        # AUDIT LOG - Required for compliance
        await self._log_service.log_create(
            session,
            user_id=str(user.id),
            created_by_id=created_by_id,
            details={
                "username": user.username,
                "is_active": user.is_active,
            },
        )

        return user

    async def update_user(
        self,
        session: AsyncSession,
        user_id: str,
        data: UserUpdate,
        updated_by_id: str,
    ) -> User:
        # Get old values for audit
        old_user = await self._repo.get_by_id(session, user_id)
        old_values = {"is_active": old_user.is_active, ...}

        # Update user
        user = await self._repo.update(session, user_id, data.model_dump())

        new_values = {"is_active": user.is_active, ...}

        # AUDIT LOG - Include old and new values
        await self._log_service.log_update(
            session,
            user_id=user_id,
            updated_by_id=updated_by_id,
            old_values=old_values,
            new_values=new_values,
        )

        return user
```

## Log Service Pattern

```python
# api/services/log_user_service.py
from db.models import LogUser

class LogUserService:
    async def log_create(
        self,
        session: AsyncSession,
        user_id: str,
        created_by_id: str,
        details: dict,
    ) -> LogUser:
        log = LogUser(
            action="CREATE",
            user_id=user_id,
            created_by_id=created_by_id,
            new_values=details,
        )
        session.add(log)
        await session.flush()
        return log

    async def log_update(
        self,
        session: AsyncSession,
        user_id: str,
        updated_by_id: str,
        old_values: dict,
        new_values: dict,
    ) -> LogUser:
        # Only log actual changes
        changes = {
            k: {"old": old_values.get(k), "new": v}
            for k, v in new_values.items()
            if old_values.get(k) != v
        }

        if not changes:
            return None

        log = LogUser(
            action="UPDATE",
            user_id=user_id,
            created_by_id=updated_by_id,
            old_values=old_values,
            new_values=new_values,
            changes=changes,
        )
        session.add(log)
        await session.flush()
        return log
```

## Hook Behavior

- **Type:** PostToolUse (advisory)
- **Trigger:** Write or Edit to `api/services/*.py` (excluding log services)
- **Action:** Prints warning message, does not block
