# Employee Meal Request System

A full-stack web application for managing employee meal requests with authentication, role-based access control, and request tracking.

## Repository Structure

```
meal_request/
├── src/
│   ├── backend/          # Python FastAPI backend application
│   │   ├── app.py        # FastAPI application entry point
│   │   ├── main.py       # Application entry point
│   │   ├── settings.py   # Pydantic settings configuration
│   │   ├── db/           # Database models and CRUD operations
│   │   ├── routers/      # API route handlers
│   │   ├── utils/        # Utility functions
│   │   ├── services/     # Business logic services
│   │   ├── tests/        # Backend test suite
│   │   └── requirements.txt
│   └── frontend/         # HTML/CSS/JS frontend application
│       ├── index.html
│       ├── login.html
│       ├── js/
│       ├── img/
│       └── libs/
├── docs/                 # Documentation and process tracking
├── scripts/              # Utility scripts and tooling
└── README.md
```

## Backend

### Requirements
- Python 3.12+
- MariaDB database
- ODBC drivers (for HRIS/BioStar external database connections)

### Setup

```bash
cd src/backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in `src/backend/` with:

```env
# Primary Database (MariaDB)
MARIA_URL=mysql+aiomysql://user:password@localhost:3306/dbname?charset=utf8mb4
# Or use individual variables:
DB_USER=meal_user
DB_PASSWORD=meal_password
DB_SERVER=localhost
DB_NAME=meal_request_db

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Active Directory (if using AD auth)
AD_SERVER=ldap://your-domain.com
AD_DOMAIN=your-domain
AD_BASE_DN=DC=your-domain,DC=com

# Application
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Optional: External databases
BIOSTAR_URL=mssql+pyodbc://...
HRIS_URL=mssql+pyodbc://...

# Observability
# Prometheus metrics are always available at /metrics
```

### Running the Application

```bash
cd src/backend

# Set PYTHONPATH to the src/backend directory
export PYTHONPATH=/path/to/meal_request/src/backend
# On Windows:
# set PYTHONPATH=C:\path\to\meal_request\src\backend

# Run with uvicorn
PYTHONPATH=src/backend python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 1013

# Or use the full path
PYTHONPATH=/home/adel/Desktop/meal_request/src/backend python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 1013
```

### Running Tests

```bash
cd src/backend

# Set PYTHONPATH before running tests
export PYTHONPATH=src/backend
# On Windows:
# set PYTHONPATH=src\backend

# Run all tests
PYTHONPATH=src/backend python3 -m pytest tests/ -v

# Run specific test file
PYTHONPATH=src/backend python3 -m pytest tests/test_settings.py -v
```

### Database Migrations

```bash
cd src/backend

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description"
```

## Frontend

The frontend is a simple HTML/CSS/JavaScript application served statically.

### Setup

No build process required. Simply serve the `src/frontend/` directory with any static file server.

```bash
# Using Python's built-in server
cd src/frontend
python3 -m http.server 3000

# Using Node.js serve (if installed)
npx serve src/frontend -l 3000
```

### Accessing the Application

- Backend API: http://localhost:1013
- Frontend: http://localhost:3000
- API Documentation: http://localhost:1013/docs (Swagger UI)

## Architecture Overview

### Backend Architecture

**Framework & Core:**
- FastAPI application with async/await support
- Multi-database support: MariaDB (primary), HRIS (SQL Server), BioStar (MSSQL)
- JWT-based authentication with access and refresh tokens
- Role-based access control (RBAC) with page permissions

**Authentication Flow:**
1. User logs in via login.html (domain or local scope)
2. Domain users: LDAP/AD authentication + local Account creation/update
3. Local users: Verification against SecurityUser table
4. JWT tokens (access + refresh) returned and stored
5. Token revocation support via `revoked_token` table
6. Frontend includes Authorization header in subsequent API calls

**Key Domain Models:**
- **Security/Auth:** SecurityUser, Account, Role, RolePermission, PagePermission, RevokedToken
- **Meal Requests:** MealRequest, MealRequestLine, MealType
- **HR Integration:** Employee, Department, DepartmentAssignment, EmployeeShift
- **Attendance:** Attendance, AttendanceDevice, AttendanceDeviceType

**Database Layer:**
- Primary: MariaDB via SQLAlchemy 2.0+ with async support (aiomysql)
- External: HRIS and BioStar databases for employee/attendance data
- CRUD operations in `db/cruds/` with async patterns
- Alembic for migrations (uses pymysql for sync operations)

**Middleware & Observability:**
- Request logging middleware
- Prometheus metrics available at `/metrics`
- OpenTelemetry support for distributed tracing
- Structured logging via `utils/logging_config.py`

### Frontend Architecture

**Structure:**
- Vanilla HTML/CSS/JavaScript (no frameworks)
- Pages: login, meal requests, request details, analytics, role management
- JavaScript modules in `js/` directory
- Third-party libraries in `libs/`

**Authentication:**
- JWT tokens stored and managed client-side
- Page permissions checked before rendering
- Token refresh on 401 responses

## Background Tasks & Celery

### Task Types

The application uses two types of background tasks:

1. **FastAPI BackgroundTasks:** For simple, non-blocking operations (e.g., sending single emails)
2. **Celery:** For scheduled jobs, long-running tasks, and complex workflows

### Celery Setup

**Installation:**
```bash
cd src/backend
pip install celery redis gevent
```

**Running Celery Worker:**
```bash
cd src/backend
export PYTHONPATH=/home/adel/Desktop/meal_request/src/backend

# Run worker with gevent pool (recommended for async tasks)
celery -A celery_app worker -P gevent --loglevel=info

# Run Celery Beat for scheduled tasks
celery -A celery_app beat --loglevel=info
```

**Available Tasks:**
- **HRIS Replication:** `hris_replication_task` - Syncs employee data from HRIS database
- **Attendance Sync:** `attendance_yesterday_task`, `attendance_today_task`, `attendance_tomorrow_task`
- **Cleanup:** `cleanup_history_task` - Removes old audit logs
- **Email:** `send_email_task` - Sends emails via Exchange Web Services

### Critical: Celery Async Task Pattern

**⚠️ MANDATORY PATTERN for all Celery tasks using async database operations:**

When writing Celery tasks with async database operations, you MUST use this pattern to avoid event loop conflicts:

```python
def _run_async(coro):
    """
    Run a coroutine, handling both standalone and event-loop contexts.

    When running in Celery with gevent, an event loop already exists.
    This function detects the context and uses the appropriate method.
    """
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        # Loop exists - run in new thread with new event loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop - use existing or create new one
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

@shared_task(bind=True, max_retries=3)
def my_async_task(self):
    async def _execute():
        from db.maria_database import database_engine

        result = None
        try:
            async with DatabaseSessionLocal() as session:
                # Your async logic here
                result = {"status": "success"}
        finally:
            # CRITICAL: Dispose engines BEFORE event loop closes
            await database_engine.dispose()

        return result

    return _run_async(_execute())
```

**Key Requirements:**
- ✅ Use the `_run_async` helper with event loop detection
- ✅ Dispose database engines in the finally block
- ✅ Return result AFTER finally block
- ❌ Never use simple `asyncio.run()` without event loop detection
- ❌ Never return from inside try blocks

See `tasks/hris.py` for reference implementation.

## Development

### Critical Development Patterns

**⚠️ MANDATORY: CamelCase Schema Convention**

ALL Pydantic request/response schemas MUST inherit from `api.schemas._base.CamelModel`:

```python
from api.schemas._base import CamelModel

class UserCreate(CamelModel):
    user_name: str  # Python: snake_case
    is_active: bool  # JSON: camelCase (automatic)
    role_id: int
```

**Rules:**
- ✅ Use `CamelModel` as base class for ALL schemas
- ✅ Use snake_case in Python code
- ✅ JSON output automatically becomes camelCase
- ❌ Never inherit from `BaseModel` directly
- ❌ Never use manual `Field(alias="...")` for camelCase
- ❌ Never return `dict` without `by_alias=True`

**Why this matters:** Frontend JavaScript expects camelCase. Breaking this causes parsing errors.

**PYTHONPATH Requirement:**

All backend operations require setting `PYTHONPATH`:

```bash
export PYTHONPATH=/home/adel/Desktop/meal_request/src/backend
# Or relative from repo root:
export PYTHONPATH=src/backend
```

**Async/Await Pattern:**
- All database operations use async/await
- Use `AsyncSession` for database operations
- FastAPI endpoints should be async

### Task Tracking

Process and task tracking is maintained in `docs/PROCESS_TASKS.md`.

### Adding New Features

1. Backend changes go in `src/backend/`
2. Frontend changes go in `src/frontend/`
3. Documentation updates go in `docs/`
4. Update task tracking in `docs/PROCESS_TASKS.md`
5. **Follow the CamelCase schema convention for all API schemas**
6. **Use the Celery async pattern for background tasks with async operations**

## Documentation Generation Policy

**Documentation is generated on explicit request only.** This prevents token waste and unnecessary file accumulation during routine code changes.

### How to Request Documentation Generation

Documentation generation is triggered by **one** of these methods:

1. **Commit Message Tag**: Include `[docs]` in your commit message
   ```bash
   git commit -m "feat: add new feature [docs]"
   ```

2. **Pull Request Label**: Add the `generate-docs` label to your PR
   - In GitHub: Use the Labels sidebar when creating/editing a PR

3. **Environment Variable**: Set `GENERATE_DOCS=true` before running scripts
   ```bash
   GENERATE_DOCS=true npm run docs:generate
   ```

### Documentation Files

Generated documentation is stored in `docs/generated/` and includes:
- **INDEX.md** - Generated documentation index
- **HTTP_LAYER.md** - HTTP communication layer documentation
- **API_REFERENCE.md** - API endpoint reference

### CI Integration

The repository uses GitHub Actions to automatically check for documentation requests. The `generate-docs` workflow:
- Runs on every push and pull request
- Only generates docs when triggers are detected
- Comments on PRs to show which triggers were used
- Does not commit docs automatically (prevents noise)

See `.github/workflows/generate-docs.yml` for workflow details.

See `docs.config.json` for configuration details.

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Run tests and linting
4. Update documentation
5. Submit a pull request

## License

[Add your license information here]
