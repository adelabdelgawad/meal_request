# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Backend Development

**Setup and Installation:**
```bash
cd src/backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Running the Application:**
```bash
cd src/backend
# Set PYTHONPATH to the src/backend directory
export PYTHONPATH=src/backend

# Run with uvicorn (default port 8000)
PYTHONPATH=src/backend python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Testing:**
```bash
cd src/backend
export PYTHONPATH=src/backend

# Run all tests
PYTHONPATH=src/backend python3 -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src/backend python3 -m pytest tests/test_settings.py -v
```

**Database Migrations (Alembic):**
```bash
cd src/backend

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description"
```

### Frontend Development

The frontend is vanilla HTML/CSS/JavaScript with no build process.

```bash
# Serve with Python's built-in server
cd src/frontend
python3 -m http.server 3000

# Or with Node.js serve
npx serve src/frontend -l 3000
```

## High-Level Architecture

### Backend Architecture

**Framework & Core:**
- FastAPI application with async/await support
- Entry point: `src/backend/main.py`
- Hierarchical settings via Pydantic Settings (`core/config.py`)
- Multi-database support (PostgreSQL primary, HRIS, BioStar for external data)

**Authentication & Security:**
- JWT-based authentication with access and refresh tokens
- Dual authentication: LDAP/Active Directory and local accounts
- Login flow in `utils/login.py` checks domain vs local scope
- Token management with revocation support via `RevokedTokenService`
- Session management via `core/sessions.py` (JWT issue/verify, fingerprinting)
- Role-based access control (RBAC) with page permissions
- Rate limiting via SlowAPI
- Security middleware and CORS allowlist management

**Database Layer:**
- Primary DB: PostgreSQL 16 (via `db/database.py`, asyncpg driver)
- Secondary DBs: HRIS (SQL Server), BioStar (MSSQL) for external data
- SQLModel (built on SQLAlchemy 2.0+) with async support
- Models in `db/model.py` using `TableModel` base class (SQLModel)
- Repository pattern: `api/repositories/` with `BaseRepository[T]`
- Service layer: `api/services/` with session-based dependency injection
- Alembic for migrations (uses psycopg2 driver for sync operations)

**Key Domain Models:**
- **Security/Auth:** SecurityUser, Account, Role, RolePermission, PagePermission, RevokedToken
- **Meal Requests:** MealRequest, MealRequestLine, MealType
- **HR Integration:** Employee, Department, DepartmentAssignment, EmployeeShift
- **Attendance:** Attendance, AttendanceDevice, AttendanceDeviceType

**Routers (API Endpoints):**
Organized in `api/routers/` by domain:
- `auth/`: login_router, auth_router, me_router, internal_auth_router
- `request/`: meal_request_router, requests_router, my_requests_router
- `setting/`: users_router, roles_router, pages_router, departments_router, meal_type_setup_router, scheduler/
- `report/`: analysis_router, audit_router, reporting_router
- `admin/`: admin_router

All routers registered via unified `api/routers/__init__.py` → `main_router`

**Dependencies (`core/dependencies.py`):**
- `SessionDep`: Async database session (annotated dependency)
- `CurrentUserDep`: Current authenticated user
- `ActiveUserDep`: Current active (non-blocked) user
- `RoleChecker`: Role-based endpoint protection

**Middleware & Utilities:**
- Correlation middleware (`core/correlation.py`) — request tracing via X-Correlation-ID
- Observability with Prometheus metrics and OpenTelemetry tracing (`utils/observability.py`)
- Structured logging via `utils/logging_config.py`
- LDAP authentication (`utils/ldap.py`)
- Email sending via Exchange Web Services (`utils/mail_sender.py`)
- Security headers middleware (in `main.py`)

**Background Processing:**
- Celery with gevent for async background tasks (Redis broker)
- Tasks in `tasks/`: hris.py, attendance.py, scheduler.py, email.py
- Flower for Celery monitoring (port 5555)
- Email notifications also use FastAPI BackgroundTasks for non-blocking execution

### Frontend Architecture

**Structure:**
- Simple HTML/CSS/JavaScript without frameworks
- Pages: login.html, meal_request.html, request_details.html, request_analysis.html, role_management.html
- JavaScript modules in `js/` directory
- Third-party libraries in `libs/`

**Authentication Flow:**
1. User logs in via login.html
2. Backend validates credentials (LDAP or local)
3. JWT tokens (access + refresh) returned and stored
4. Subsequent API calls include Authorization header
5. Frontend checks page permissions before rendering

### Database Architecture

**Primary (PostgreSQL 16):**
- Application data: users, roles, meal requests, permissions
- Managed via SQLModel + Alembic migrations
- Uses asyncpg for async operations, psycopg2 for Alembic sync operations
- Connection pooling via `DatabaseManager` in `db/database.py`

**External Databases:**
- **HRIS:** SQL Server database for employee records (read-only, via `db/hris_database.py`)
- **BioStar:** Attendance system database (read-only)

**Database Session Management:**
- `get_application_session()` provides async session per request (dependency injection)
- `SessionDep` annotated type for FastAPI endpoint injection
- Sessions auto-rollback on exceptions and close after response
- Multiple database connections managed separately

## Configuration

**Environment Variables:**
Create `.env` file in `src/backend/` or use Docker env files (`docker/env/.env.backend`):

```env
# Primary Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://meal_user:meal_password@localhost:5432/meal_request_db
# Legacy fallbacks also supported: MARIA_URL, APP_DB_URL

# External Database URLs
DATABASE_HRIS_URL=mssql+pyodbc://...

# JWT / Secrets (prefix: SECRET_)
SECRET_JWT_SECRET_KEY=your-secret-key
SECRET_JWT_ALGORITHM=HS256
# Legacy fallback: JWT_SECRET_KEY

# LDAP/Active Directory (prefix: AD_)
AD_SERVER=ldap://domain.com
AD_DOMAIN=domain
AD_SERVICE_ACCOUNT=service_account
AD_SERVICE_PASSWORD=service_password

# CORS (prefix: API_)
API_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
# Legacy fallback: ALLOWED_ORIGINS (comma-separated)

# Redis (prefix: REDIS_)
REDIS_URL=redis://localhost:6379/0

# Celery (prefix: CELERY_)
CELERY_ENABLED=true
# CELERY_BROKER_URL defaults to REDIS_URL

# Session (prefix: SESSION_)
SESSION_ACCESS_TOKEN_MINUTES=15
SESSION_REFRESH_LIFETIME_DAYS=30
SESSION_MAX_CONCURRENT=5

# Locale (prefix: LOCALE_)
LOCALE_DEFAULT_LOCALE=en
LOCALE_SUPPORTED_LOCALES=["en","ar"]

# Application
ENVIRONMENT=local  # local, development, production
LOG_LEVEL=INFO
```

**Settings Management (`core/config.py`):**
Hierarchical settings with sub-settings classes:
- `settings.api.*` (APISettings, prefix `API_`) — CORS, API metadata
- `settings.database.*` (DatabaseSettings, prefix `DATABASE_`) — DB URLs
- `settings.sec.*` (SecretSettings, prefix `SECRET_`) — JWT config
- `settings.redis.*` (RedisSettings, prefix `REDIS_`) — Redis connection, cache TTLs
- `settings.ldap.*` (LDAPSettings, prefix `AD_`) — LDAP/AD config
- `settings.celery.*` (CelerySettings, prefix `CELERY_`) — Celery broker
- `settings.email.*` (EmailSettings, prefix `SMTP_`) — Email config
- `settings.locale.*` (LocaleSettings, prefix `LOCALE_`) — i18n config
- `settings.session.*` (SessionSettings, prefix `SESSION_`) — Session/token lifetimes
- `settings.attendance.*` (AttendanceSettings, prefix `ATTENDANCE_`) — Attendance sync
- `settings.rate_limit.*` (RateLimitSettings, prefix `RATE_LIMIT_`) — Rate limiting
- Top-level: `settings.environment`, `settings.log_level`, `settings.enable_json_logs`

Legacy env vars (`MARIA_URL`, `JWT_SECRET_KEY`, `ALLOWED_ORIGINS`, `APP_DB_URL`) are supported via `model_post_init` for backward compatibility.

Secrets loaded from vault in non-local environments via `utils/secrets.py`.
Metrics always available at `/metrics` endpoint.

## Important Implementation Patterns

### PYTHONPATH Requirement
The backend requires `PYTHONPATH` to be set to `src/backend` for imports to work correctly. Always set this before running the app or tests.

### **CRITICAL — Schema CamelCase Convention (MANDATORY)**

**ALL Pydantic request/response schemas MUST inherit from `api.schemas._base.CamelModel`**

This enforces camelCase JSON keys required by the frontend JavaScript ecosystem.

**Rules:**
1. **Import and subclass CamelModel for ALL new schemas:**
   ```python
   from api.schemas._base import CamelModel

   class UserCreate(CamelModel):
       user_name: str  # Python uses snake_case
       is_active: bool
       role_id: int
   ```

2. **DO NOT implement local alias generators or duplicate alias configuration.**
   - Never use `alias_generator` in individual schemas
   - Never manually define `Field(alias="...")` for camelCase conversion
   - All aliasing is handled by CamelModel base class

3. **When returning API responses:**
   - Return Pydantic model instances directly (FastAPI handles serialization)
   - OR use `.model_dump(by_alias=True)` for manual serialization
   ```python
   @router.get("/users/{id}", response_model=UserResponse)
   async def get_user(id: int):
       user = await service.get_user(id)
       return user  # FastAPI auto-serializes with camelCase
   ```

4. **Field naming conventions:**
   - Python code: Use `snake_case` (e.g., `full_name`, `is_active`, `role_id`)
   - JSON output: Automatically becomes `camelCase` (e.g., `fullName`, `isActive`, `roleId`)
   - Frontend input: Accepts both `snake_case` and `camelCase` (via `populate_by_name=True`)

**Why this matters:**
- Frontend JavaScript/TypeScript expects camelCase keys
- Breaking this convention causes frontend parsing errors and UI bugs
- Centralizing alias generation prevents configuration drift
- Ensures consistent API contract across all endpoints

**Testing:**
- Run `pytest tests/schemas/test_camel_model.py` to verify schema aliasing
- Run `pytest tests/api/test_response_aliasing.py` to verify endpoint responses
- Always validate JSON output against frontend contract before merging

**DO NOT:**
- ❌ Create schemas inheriting from `BaseModel` directly
- ❌ Use `Field(alias="camelCase")` manually
- ❌ Return `dict` without `by_alias=True`
- ❌ Mix snake_case in API responses

**Example violation (WRONG):**
```python
# BAD - Don't do this!
from pydantic import BaseModel, Field

class UserCreate(BaseModel):  # ❌ Wrong base class
    user_name: str = Field(alias="userName")  # ❌ Manual alias
```

**Correct pattern:**
```python
# GOOD - Do this!
from api.schemas._base import CamelModel

class UserCreate(CamelModel):  # ✅ Correct base class
    user_name: str  # ✅ Auto-aliased to "userName"
```

**Failure to follow this will break frontend integration.**

### Async/Await Everywhere
- All database operations use async/await
- FastAPI endpoints are async
- Use `AsyncSession` for database operations

### Authentication Pattern
Login flow (`utils/login.py`):
1. Check if scope is "domain" or "local"
2. For domain: authenticate via LDAP, create/update local Account record
3. For local: verify against SecurityUser table
4. Check user is not deleted/locked
5. Return Account object with role information

### Token Management
- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 30 days (configurable)
- Both tokens include unique JTI (JWT ID) for revocation
- Revoked tokens stored in `revoked_token` table
- Token verification checks revocation status

### RBAC Pattern
- Users have Roles via Account model
- Roles have permissions via RolePermission
- Pages have access control via PagePermission
- Check permissions in routers using utility functions

### Repository + Service Pattern
**Repositories** (`api/repositories/`): Data access layer
- Inherit from `BaseRepository[T]` (generic over SQLModel type)
- Receive session in `__init__`: `repo = UserRepository(session)`
- Methods: `get_by_id()`, `get_all()`, `create()`, `update()`, `delete()`

**Services** (`api/services/`): Business logic layer
- Receive session in `__init__`: `service = UserService(session)`
- Instantiate repositories internally
- Handle validation, authorization, audit logging

**Router pattern:**
```python
@router.get("/users/{id}")
async def get_user(id: int, session: SessionDep, user: CurrentUserDep):
    service = UserService(session)
    return await service.get_user(id)
```

### Background Tasks
Email notifications use FastAPI BackgroundTasks for non-blocking execution:
```python
from fastapi import BackgroundTasks

@router.post("/endpoint")
async def endpoint(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_function, args...)
```

### **CRITICAL — Celery Async Tasks Pattern (MANDATORY)**

**When writing Celery tasks that use async database operations, you MUST follow this exact pattern to avoid event loop conflicts.**

**Background:**
- Celery workers run with gevent (-P gevent) which patches asyncio and creates an event loop
- Simply using `asyncio.run()` will conflict with the existing loop, causing:
  - `RuntimeError: Task got Future attached to a different loop`
  - `Event loop is closed` errors
  - Database connection cleanup failures

**Required Pattern for ALL Async Celery Tasks:**

**1. Use the correct `_run_async` helper (copy from `tasks/hris.py`):**

```python
def _run_async(coro):
    """
    Run a coroutine, handling both standalone and event-loop contexts.

    When running in Celery with gevent, an event loop already exists.
    When running standalone (e.g., tests), we need to create one.

    This function detects the context and uses the appropriate method.
    """
    import asyncio

    # Try to get the current running loop
    try:
        loop = asyncio.get_running_loop()
        # Loop is running - we need to run in a new thread with a new event loop
        logger.debug("Detected running event loop - running coroutine in new thread")
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - try to get existing loop or create one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the coroutine
        logger.debug("No running event loop - using run_until_complete")
        try:
            return loop.run_until_complete(coro)
        finally:
            # Don't close the loop if it's the default event loop
            # as it might be reused by Celery
            pass
```

**2. Structure your task with proper engine disposal:**

```python
@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,))
def my_async_celery_task(self, arg1, arg2):
    """Celery task that uses async database operations."""

    async def _execute():
        from db.database import AsyncSessionLocal as DatabaseSessionLocal, engine as database_engine
        from db.hris_database import _get_hris_session_maker, dispose_hris_engine

        # Initialize result variable
        result = None

        try:
            # Create sessions within the event loop
            async with DatabaseSessionLocal() as app_session:
                HrisSessionLocal = _get_hris_session_maker()
                async with HrisSessionLocal() as hris_session:
                    try:
                        # Your async logic here
                        # ... do work ...

                        # Store result (don't return yet!)
                        result = {"status": "success", "data": "..."}

                    except Exception as e:
                        logger.error(f"Error: {e}")
                        raise
                    finally:
                        # Any cleanup inside sessions (if needed)
                        pass

        except Exception as e:
            logger.error(f"Outer error: {e}")
            raise
        finally:
            # CRITICAL: Dispose engines BEFORE event loop closes
            # This prevents "Event loop is closed" warnings
            logger.debug("Disposing database engines...")
            try:
                await dispose_hris_engine()
                logger.debug("HRIS engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose HRIS engine: {e}")

            try:
                await database_engine.dispose()
                logger.debug("Maria engine disposed")
            except Exception as e:
                logger.warning(f"Failed to dispose Maria engine: {e}")

        # Return AFTER finally blocks
        return result

    try:
        logger.info("Starting task...")
        result = _run_async(_execute())
        logger.info("Task completed")
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
```

**Key Requirements:**

1. ✅ **Use the sophisticated `_run_async` helper** that detects and handles existing event loops
2. ✅ **Initialize result variable** at the start of `_execute()`
3. ✅ **Wrap async with blocks in try/except/finally**
4. ✅ **Dispose database engines in the finally block** (inside `_execute()`, not outside)
5. ✅ **Return result AFTER the finally block**, not inside try/except
6. ✅ **Call engines in correct order**: dispose HRIS first, then Maria

**DO NOT:**
- ❌ Use simple `asyncio.run(coro)` without event loop detection
- ❌ Return from inside try blocks (prevents finally from executing properly)
- ❌ Forget to dispose database engines (causes connection leaks)
- ❌ Dispose engines outside the `_execute()` coroutine (too late, loop already closed)
- ❌ Use `async with` without wrapping in try/finally for engine disposal

**Working Examples:**
- ✅ `tasks/hris.py` - `hris_replication_task` (REFERENCE IMPLEMENTATION)
- ✅ `tasks/attendance.py` - All three attendance tasks
- ✅ `tasks/scheduler.py` - `cleanup_history_task`

**Synchronous Tasks (No Pattern Needed):**
- `tasks/email.py` - Email tasks use sync EmailSender, no async operations

**Why This Matters:**
- Gevent creates an event loop in the worker greenlet
- Database engines bind connections to event loops
- Improper cleanup leaves connections bound to closed loops
- Results in resource leaks and runtime errors
- Following this pattern ensures clean resource management

**Testing:**
- Run Celery worker: `celery -A celery_app worker -P gevent --loglevel=info`
- Trigger async tasks and check logs for:
  - No "Event loop is closed" warnings
  - Successful engine disposal messages
  - No "attached to a different loop" errors

**Failure to follow this pattern will cause runtime errors in production.**

## Task Tracking

Implementation progress tracked in `docs/PROCESS_TASKS.md` with commit references and timestamps. When completing major features, update this tracker.

## Docker Development

```bash
cd docker/

# Start all core services
docker-compose up -d

# Start with dev tools (Redis Commander)
docker-compose --profile tools up -d

# Run database migrations
docker-compose exec backend alembic upgrade head
```

## Accessing the Application

- **Backend API:** http://localhost:8000
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **Metrics:** http://localhost:8000/metrics (Prometheus format)
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3001
- **Flower (Celery):** http://localhost:5555

## Testing

### Backend Tests
```bash
cd src/backend
PYTHONPATH=src/backend python3 -m pytest tests/ -v

# Key test files:
# tests/test_settings.py — Hierarchical settings validation
# tests/test_locale_detection.py — Locale detection precedence
# tests/test_security.py — JWT and authentication
# tests/test_single_session_per_request.py — Session management
# tests/test_response_aliasing.py — CamelCase API responses
# tests/test_user_sync_conflict.py — HRIS sync conflict resolution
# tests/test_hris_on_shift_logic.py — Attendance shift logic
```

---

## User Source Tracking and HRIS Sync Conflict Resolution (Strategy A)

**Problem:** HRIS replication was deactivating all users including manual users (contractors, service accounts) and users that admins wanted to keep active despite HRIS deletion.

**Solution:** Strategy A implements source tracking and status override functionality.

### User Source Types (Simplified)

Users are classified by their `user_source` field (only 2 values):

| Source | Description | HRIS Sync Behavior |
|--------|-------------|-------------------|
| **hris** | User synced from HRIS system | Fully managed by HRIS sync |
| **manual** | User created manually by admin | **Skipped** by HRIS sync |

**Note:** The `ldap` source type was removed in migration `8def5142d20`. Existing LDAP users were migrated to:
- `hris` if linked to HRIS employee (is_domain_user=TRUE AND employee_id IS NOT NULL)
- `manual` otherwise

### Localized Source Metadata

Each source type includes bilingual labels and descriptions:

```python
# Backend provides structured metadata
GET /api/v1/admin/user-sources
[
  {
    "code": "hris",
    "name_en": "HRIS User",
    "name_ar": "مستخدم HRIS",
    "description_en": "User synchronized from the HRIS system...",
    "description_ar": "مستخدم متزامن من نظام الموارد البشرية...",
    "icon": "database",
    "color": "blue",
    "can_override": true
  },
  {
    "code": "manual",
    "name_en": "Manual User",
    "name_ar": "مستخدم يدوي",
    "description_en": "User created manually by an administrator...",
    "description_ar": "مستخدم تم إنشاؤه يدويًا بواسطة المسؤول...",
    "icon": "user-edit",
    "color": "green",
    "can_override": false
  }
]
```

**Frontend Usage:**
- Render source badges using `name_en` / `name_ar` based on locale
- Show tooltips with `description_en` / `description_ar`
- Apply consistent colors and icons from metadata

### Status Override

HRIS users can have status override enabled to prevent HRIS sync from modifying their `is_active` status:

**Fields:**
- `status_override` (boolean): If true, HRIS sync skips this user
- `override_reason` (text): Admin-provided justification (required, min 20 chars)
- `override_set_by_id` (UUID): Admin who enabled override
- `override_set_at` (timestamp): When override was enabled

### HRIS Sync Behavior

During HRIS replication (`utils/replicate_hris.py`):

1. **Phase 1-5**: Standard HRIS sync (employees, security users, department assignments)
2. **Phase 6 (NEW)**: Sync `User.is_active` based on `SecurityUser.is_deleted/is_locked`
   - **Deactivates** HRIS users whose SecurityUser is deleted OR locked
   - **Reactivates** HRIS users whose SecurityUser is active
   - **Skips** manual users (`user_source='manual'`)
   - **Skips** override users (`status_override=True`)

**Sync Statistics Logged:**
- `deactivated`: Number of HRIS users deactivated
- `reactivated`: Number of HRIS users reactivated
- `skipped_manual`: Number of manual users preserved
- `skipped_override`: Number of override users preserved

### Admin Endpoints

**Mark User as Manual:**
```http
POST /api/v1/admin/users/{user_id}/mark-manual
Authorization: Bearer {admin_token}

{
  "reason": "External contractor without HRIS record"
}
```

**Enable Status Override:**
```http
POST /api/v1/admin/users/{user_id}/override-status
Authorization: Bearer {admin_token}

{
  "statusOverride": true,
  "overrideReason": "Terminated employee kept for historical audit access"
}
```

**Disable Status Override:**
```http
POST /api/v1/admin/users/{user_id}/override-status
Authorization: Bearer {admin_token}

{
  "statusOverride": false
}
```

### Database Schema

**Migrations:**
1. `2025_12_15_1010-122274de80f...` - Add user_source and status_override fields
2. `2025_12_15_1023-8def5142d20...` - Remove 'ldap' from user_source enum (simplified to hris/manual)

**New Fields in `user` table:**
```sql
user_source ENUM('hris', 'manual') NOT NULL DEFAULT 'hris'
status_override BOOLEAN NOT NULL DEFAULT FALSE
override_reason TEXT NULL
override_set_by_id CHAR(36) NULL -- FK to user.id
override_set_at DATETIME NULL
```

**Index:** Composite index on `(user_source, status_override)` for sync performance

**New Endpoint:**
```http
GET /api/v1/admin/user-sources
# Returns localized metadata for all user source types
# No authentication required (public metadata)
```

### Use Cases

**1. Contractor Account (Manual User)**
```python
# Admin creates contractor manually
user = User(
    username="contractor_john",
    user_source="manual",  # Will never be touched by HRIS sync
    is_active=True,
    password="hashed_password"
)
```

**2. Terminated Employee (Override User)**
```python
# Employee terminated in HRIS but kept for audit
# Admin enables override via API endpoint
user.status_override = True
user.override_reason = "Terminated but kept for historical access to reports"
user.override_set_by_id = admin_user_id
user.override_set_at = datetime.now(timezone.utc)

# HRIS sync will NOT deactivate this user despite SecurityUser.is_deleted=True
```

**3. HRIS User (Standard Flow)**
```python
# User from HRIS, no override
user.user_source = "hris"
user.status_override = False

# HRIS sync controls is_active based on SecurityUser.is_deleted/is_locked
```

### Testing

**Test File:** `src/backend/tests/test_user_sync_conflict.py`

**Test Coverage:**
- ✅ Manual users preserved during HRIS sync
- ✅ Override users preserved during HRIS sync
- ✅ HRIS users deactivated when SecurityUser deleted
- ✅ HRIS users deactivated when SecurityUser locked
- ✅ HRIS users reactivated when SecurityUser active
- ✅ Mixed user scenarios (manual + override + HRIS)

**Run Tests:**
```bash
PYTHONPATH=src/backend python3 -m pytest tests/test_user_sync_conflict.py -v
```

### Audit Logging

All override operations are logged via `LogPermissionService`:

**Operation Types:**
- `user_marked_manual`: User source changed to manual
- `user_status_override_changed`: Override enabled/disabled

**Log Details Include:**
- Admin user ID who performed action
- Reason provided
- Previous state (for mark-manual)

### Troubleshooting

**Issue:** User deactivated despite being manual
- **Check:** Verify `user_source='manual'` in database
- **Solution:** Run mark-manual endpoint or update directly

**Issue:** Override not working
- **Check:** Verify `status_override=True` and `user_source='hris'`
- **Note:** Override only works for HRIS users, not manual users

**Issue:** HRIS sync statistics incorrect
- **Check:** Review logs for sync phase 6 output
- **Debug:** Check `User.user_source` and `User.status_override` values

### API Response Schema

**UserResponse** now includes Strategy A fields:
```json
{
  "id": "uuid",
  "username": "john_doe",
  "isActive": true,
  "userSource": "hris",  // NEW: 'hris', 'manual', or 'ldap'
  "statusOverride": false,  // NEW
  "overrideReason": null,  // NEW
  "overrideSetById": null,  // NEW
  "overrideSetAt": null  // NEW
}
```

Frontend can display:
- Badge showing user source (HRIS/Manual/LDAP)
- Override indicator with reason tooltip
- Admin actions (Mark Manual, Enable Override) for authorized users

### Migration Notes

**Automatic Backfill:**
Migration automatically classifies existing users:
- `is_domain_user=False` → `user_source='manual'`
- `is_domain_user=True` AND `employee_id NOT NULL` → `user_source='hris'`
- `is_domain_user=True` AND `employee_id IS NULL` → `user_source='ldap'`

**No Downtime:**
- Migration adds columns with safe defaults
- Code deployment can happen immediately after migration
- Rollback available via downgrade migration

---

- NEVER commit or do a git actions until the user asked for that
- Never create md file for documentation or change summary until the user asked this from you