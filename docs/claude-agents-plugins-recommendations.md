# Claude Agents and Plugins Recommendations

Based on comprehensive analysis of the Employee Meal Request System codebase (backend, frontend, infrastructure), this document recommends Claude Agents and Plugins tailored to enhance development productivity.

---

## Part 1: Recommended Claude Agents

### 1. Backend Architecture Agent

**Purpose:** Enforce FastAPI structure, service/repository patterns, and maintain architectural consistency across the backend codebase.

**What it understands:**
- 15+ FastAPI routers in `api/v1/`
- 29 stateless repositories in `api/repositories/`
- Stateless service classes in `api/services/`
- Domain exception hierarchy in `core/exceptions.py`
- Dependency injection via FastAPI `Depends()`

**Typical tasks:**
- Review new endpoint implementations for pattern compliance
- Validate router registration and response model aliasing
- Check service-repository coupling patterns
- Ensure exception handling follows domain exception types
- Verify pagination implementation consistency

**Why it improves productivity:**
- Your backend has 111+ API files with consistent patterns - manual review is error-prone
- Stateless service instantiation pattern is easy to violate
- Dependency injection chains require explicit verification

**Type:** Enforcement + Advisory

---

### 2. CamelModel Schema Agent

**Purpose:** Enforce the MANDATORY CamelModel inheritance convention for all Pydantic schemas to prevent frontend integration breakage.

**What it understands:**
- `api/schemas/_base.CamelModel` base class implementation
- Field aliasing via `alias_generator=to_camel`
- Response serialization with `by_alias=True`
- Schema triad pattern (Create/Response/Update)
- UTC datetime serialization with 'Z' suffix

**Typical tasks:**
- Review all new/modified Pydantic schemas
- Flag direct `BaseModel` inheritance (violation)
- Flag manual `Field(alias="...")` usage (violation)
- Validate `.model_dump(by_alias=True)` in manual serialization
- Check response_model configuration in routers

**Why it improves productivity:**
- Breaking this convention causes silent frontend JSON parsing errors
- 110+ API files with schemas - easy to introduce violations
- CLAUDE.md explicitly marks this as CRITICAL convention

**Type:** Enforcement (blocking)

---

### 3. Celery Async Task Agent

**Purpose:** Ensure all Celery tasks using async database operations follow the mandatory `_run_async()` pattern to prevent event loop conflicts.

**What it understands:**
- Celery + gevent pool architecture
- Event loop detection in `_run_async()` helper
- Engine disposal timing in `finally` blocks
- Multi-database session management (MariaDB, HRIS)
- Reference implementation in `tasks/hris.py`

**Typical tasks:**
- Review new Celery task implementations
- Verify `_run_async()` helper usage (not simple `asyncio.run()`)
- Check engine disposal order (HRIS first, then Maria)
- Ensure result variables initialized before try blocks
- Validate return statements after finally blocks

**Why it improves productivity:**
- Incorrect patterns cause "Event loop is closed" errors in production
- Each async Celery task requires 6+ specific requirements
- Reference implementation is 80+ lines of boilerplate

**Type:** Enforcement + Advisory

---

### 4. HRIS Sync Specialist Agent

**Purpose:** Manage HRIS replication logic, user source tracking, and status override functionality to prevent sync conflicts.

**What it understands:**
- User source enum (`hris`, `manual`)
- Status override mechanism (flag, reason, set_by, set_at)
- Six-phase HRIS replication in `utils/replicate_hris.py`
- SecurityUser to User synchronization
- Employee, Department, DepartmentAssignment sync

**Typical tasks:**
- Review changes to HRIS sync logic
- Validate user source classification rules
- Ensure status override logic respects manual users
- Check audit logging for override operations
- Verify deactivation/reactivation sync statistics

**Why it improves productivity:**
- HRIS sync touches authentication, permissions, and meal requests
- Incorrect sync can deactivate manual users (contractors, service accounts)
- Strategy A implementation requires understanding across 5+ files

**Type:** Advisory + Execution

---

### 5. Frontend Page Integrity Agent

**Purpose:** Ensure new Next.js pages follow server/client component patterns, routing conventions, and data fetching best practices.

**What it understands:**
- App Router structure (`(auth)`, `(pages)` route groups)
- Server component vs. client component patterns
- `_components/` directory convention for internal components
- Server Actions in `lib/actions/`
- SWR usage for client-side data revalidation
- `RequireAuth` and role-based protection patterns

**Typical tasks:**
- Review new page implementations
- Validate `'use client'` directive usage
- Check data fetching patterns (server actions vs. API routes)
- Ensure mobile responsiveness patterns
- Verify locale integration with `useLanguage()`

**Why it improves productivity:**
- Next.js 16 has strict server/client boundaries
- Feature pages (`/requests`, `/analytics`) follow specific composition patterns
- Breaking conventions causes hydration errors or security issues

**Type:** Advisory + Enforcement

---

### 6. Database Migration Safety Agent

**Purpose:** Review database schema changes and Alembic migrations for safety, backward compatibility, and production impact.

**What it understands:**
- SQLAlchemy 2.0+ model definitions in `db/models.py`
- Alembic migration patterns and naming conventions
- UUID storage as CHAR(36) convention
- Soft delete patterns (`is_deleted`, `is_active`)
- Relationship definitions and cascade behavior
- Bilingual field patterns (`_en`, `_ar` suffixes)

**Typical tasks:**
- Review model changes for migration requirements
- Validate new migrations for rollback safety
- Check for breaking schema changes (column drops, type changes)
- Ensure index definitions for query performance
- Verify foreign key constraints and cascades

**Why it improves productivity:**
- `models.py` is 1,954 lines - changes have wide impact
- No CI/CD migration validation currently exists
- Production has 3-instance load balancing requiring safe migrations

**Type:** Advisory (pre-commit)

---

### 7. Token & Session Agent

**Purpose:** Review authentication token management, session handling, and revocation patterns for security and correctness.

**What it understands:**
- JWT access tokens (15 min default) with JTI
- Refresh tokens in HttpOnly cookies (30 days)
- Token revocation via `revoked_token` table
- Redis caching for revocation checks
- Frontend token manager (`token-manager.ts`)
- Server-side auth validation (`check-token.ts`)

**Typical tasks:**
- Review token generation and validation changes
- Check revocation handling in verify_access_token
- Validate cookie settings (Secure, HttpOnly, SameSite)
- Ensure token refresh flow correctness
- Review rate limiting on auth endpoints

**Why it improves productivity:**
- Auth touches every protected endpoint
- Token revocation requires multi-layer checks (DB + Redis)
- Frontend/backend token lifecycle must stay synchronized

**Type:** Enforcement + Advisory

---

### 8. Audit Logging Agent

**Purpose:** Ensure all write operations include proper audit logging with consistent patterns across services.

**What it understands:**
- 7 audit log services (LogUser, LogPermission, LogRole, LogMealRequest, etc.)
- Success/failure logging pattern in endpoints
- Action type conventions (create, update, delete, login, etc.)
- Admin ID capture from JWT payload
- Result object structure for success/failure cases

**Typical tasks:**
- Review new endpoints for audit logging completeness
- Validate audit log service usage patterns
- Check error paths include failure logging
- Ensure admin_id capture from authenticated user
- Verify audit log queries in reporting endpoints

**Why it improves productivity:**
- Audit logging is required for compliance
- Pattern is repeated across 20+ router files
- Easy to miss error path logging

**Type:** Enforcement

---

### 9. Localization Consistency Agent

**Purpose:** Ensure bilingual support (English/Arabic) is correctly implemented across backend responses and frontend components.

**What it understands:**
- Backend bilingual fields (`name_en`, `name_ar`, `description_en`, `description_ar`)
- Locale detection hierarchy (query → cookie → user pref → header → default)
- Frontend `useLanguage()` hook and translation files
- RTL support and Cairo font usage
- LocaleManager cookie persistence

**Typical tasks:**
- Review new models for bilingual field completeness
- Validate locale fallback logic in services
- Check frontend translation file updates
- Ensure RTL-compatible CSS for new components
- Verify backend locale API integration

**Why it improves productivity:**
- Bilingual support spans entire stack (models → API → frontend)
- Missing translations cause user-facing bugs
- RTL layout issues are easy to introduce

**Type:** Advisory

---

### 10. Safe Refactor Agent

**Purpose:** Provide impact analysis and safety checks for refactoring operations across the codebase.

**What it understands:**
- Cross-file dependencies in monolithic `models.py`
- Repository-service coupling patterns
- Router endpoint dependencies
- Frontend API integration points
- Type definitions shared between frontend/backend

**Typical tasks:**
- Analyze impact of model field changes
- Identify all usages of services being refactored
- Check endpoint signature changes against frontend calls
- Validate type definition consistency after changes
- Suggest safe refactoring sequences

**Why it improves productivity:**
- Codebase has 111+ backend files with tight coupling
- Frontend relies on exact API contracts
- No automated integration tests to catch breakage

**Type:** Advisory (pre-refactor analysis)

---

## Part 2: Recommended Claude Plugins

### 1. FastAPI Structure Enforcement Plugin

**Scope:** Validates all new/modified files in `api/v1/`, `api/services/`, `api/repositories/`

**When it activates:**
- On file creation in router/service/repository directories
- On modification to existing API files
- On pull request reviews touching API layer

**Rules it enforces:**
1. Router endpoints use `response_model_by_alias=True`
2. Services are stateless (no instance state, instantiate in endpoints)
3. Repositories pass session explicitly to all methods
4. Exception handling uses domain exceptions (NotFoundError, ConflictError, etc.)
5. Pagination uses `calculate_offset()` and returns (items, total)

**Mistakes it prevents:**
- Inconsistent response aliasing causing frontend JSON errors
- Stateful services causing request isolation bugs
- Raw database exceptions leaking to clients
- Off-by-one pagination errors

**Supports:** Review, Generation

---

### 2. CamelModel Schema Validation Plugin

**Scope:** All Pydantic schema definitions in `api/schemas/`

**When it activates:**
- On any schema file creation or modification
- On code generation involving Pydantic models
- On pull request reviews

**Rules it enforces:**
1. All schemas inherit from `CamelModel` (not `BaseModel`)
2. No manual `Field(alias="...")` for camelCase conversion
3. No `alias_generator` in individual schemas
4. Response returns use model instances (not raw dicts without `by_alias`)
5. Datetime fields use UTC-aware types

**Mistakes it prevents:**
- Frontend JSON parsing failures (snake_case instead of camelCase)
- Duplicate aliasing configuration
- Inconsistent API contracts
- Timezone-naive datetime serialization

**Supports:** Review, Refactor, Generation

---

### 3. Celery Task Pattern Plugin

**Scope:** All files in `tasks/` directory

**When it activates:**
- On Celery task file creation or modification
- On any `@shared_task` decorator usage

**Rules it enforces:**
1. Async tasks use `_run_async()` helper (not bare `asyncio.run()`)
2. Result variables initialized at start of `_execute()` coroutine
3. Engine disposal in `finally` blocks (inside `_execute()`)
4. Return statements after `finally` blocks (not inside try/except)
5. Proper error logging with task context

**Mistakes it prevents:**
- "Event loop is closed" errors in production
- "Task got Future attached to different loop" errors
- Connection leaks from undisposed engines
- Silent task failures without proper logging

**Supports:** Review, Generation

---

### 4. Database Model Safety Plugin

**Scope:** `db/models.py` and Alembic migration files

**When it activates:**
- On model file modifications
- On migration file creation
- On any SQLAlchemy model changes

**Rules it enforces:**
1. UUID columns use `CHAR(36)` (not UUID type)
2. Soft delete fields (`is_deleted`/`is_active`) present where required
3. Timestamp fields use `DateTime(timezone=True)` with server defaults
4. Relationships have `back_populates` for bidirectional access
5. Bilingual entities have both `_en` and `_ar` fields

**Mistakes it prevents:**
- UUID comparison failures in MySQL
- Hard deletes in audit-required tables
- Timezone-naive datetime storage
- Missing reverse relationship navigation
- Incomplete bilingual support

**Supports:** Review, Refactor

---

### 5. Frontend Component Pattern Plugin

**Scope:** All files in `src/my-app/app/`, `src/my-app/components/`

**When it activates:**
- On component file creation or modification
- On page file creation
- On layout file changes

**Rules it enforces:**
1. Server components don't use hooks (useState, useEffect, etc.)
2. Client components have `'use client'` directive
3. Data fetching in server components uses server actions
4. Client data fetching uses SWR patterns
5. Components use `useLanguage()` for i18n (not hardcoded strings)

**Mistakes it prevents:**
- Hydration mismatches from server/client boundary violations
- Stale data from improper SWR configuration
- Missing translations causing broken UI
- Client-side data fetching in server components

**Supports:** Review, Generation

---

### 6. Authentication Flow Plugin

**Scope:** `lib/auth/`, `app/api/auth/`, backend `api/v1/login.py`, `core/sessions.py`

**When it activates:**
- On auth-related file modifications
- On protected route changes
- On token handling modifications

**Rules it enforces:**
1. Token verification checks revocation status
2. Refresh tokens use HttpOnly cookies
3. Access tokens include JTI for revocation
4. Protected endpoints use `Depends(require_admin)` or equivalent
5. Rate limiting applied to login endpoints

**Mistakes it prevents:**
- Revoked tokens being accepted
- Token exposure via non-HttpOnly cookies
- Missing authorization on sensitive endpoints
- Brute force attacks on auth endpoints

**Supports:** Review

---

### 7. Deletion & Refactor Risk Plugin

**Scope:** All file deletions and significant refactors

**When it activates:**
- On file deletion
- On function/class renaming
- On endpoint URL changes
- On model field removal

**Rules it enforces:**
1. Deleted functions have no remaining callers
2. Renamed endpoints update all frontend API calls
3. Removed model fields have migration handling
4. Deleted files are not imported elsewhere
5. API endpoint changes are reflected in types

**Mistakes it prevents:**
- Import errors from deleted modules
- 404 errors from changed endpoints
- Migration failures from missing columns
- Type errors from outdated definitions

**Supports:** Review, Refactor

---

### 8. Audit Trail Completeness Plugin

**Scope:** All router endpoints with write operations (POST, PUT, PATCH, DELETE)

**When it activates:**
- On new endpoint creation
- On write endpoint modification
- On service method changes

**Rules it enforces:**
1. Write endpoints include success audit logging
2. Error paths include failure audit logging
3. Audit logs capture admin_id from JWT payload
4. Action types follow conventions (create, update, delete, etc.)
5. Result objects include relevant identifiers

**Mistakes it prevents:**
- Missing audit trails for compliance
- Incomplete error path logging
- Wrong admin attribution in logs
- Inconsistent action type naming

**Supports:** Review, Generation

---

### 9. Environment Configuration Plugin

**Scope:** Settings files, `.env.example` files, Docker configurations

**When it activates:**
- On settings.py modifications
- On new environment variable usage
- On Docker compose changes

**Rules it enforces:**
1. New env vars have defaults or clear error messages
2. Secret variables are not committed (JWT_SECRET_KEY, passwords)
3. Database URLs follow expected format
4. CORS origins are properly parsed
5. Environment-specific overrides are documented

**Mistakes it prevents:**
- Missing env vars causing startup failures
- Secrets committed to repository
- Malformed database connection strings
- CORS misconfigurations blocking frontend

**Supports:** Review

---

### 10. Test Coverage Gap Plugin

**Scope:** New features and modified code paths

**When it activates:**
- On significant code changes
- On new endpoint creation
- On service logic modifications

**Rules it enforces:**
1. New endpoints have corresponding test files
2. Service methods have unit test coverage
3. Schema changes have contract tests
4. Auth flows have integration tests
5. Critical paths have E2E test coverage

**Mistakes it prevents:**
- Untested code paths reaching production
- Regression bugs from unverified changes
- Schema contract violations
- Auth bypass vulnerabilities

**Supports:** Review, Advisory

---

## Priority Matrix

### Immediate Implementation (High Impact, Addresses Current Pain Points)

| Agent/Plugin | Reason |
|--------------|--------|
| CamelModel Schema Agent | CRITICAL convention per CLAUDE.md |
| CamelModel Schema Validation Plugin | Prevents frontend breakage |
| Celery Async Task Agent | Prevents production event loop errors |
| Celery Task Pattern Plugin | Enforces complex mandatory pattern |
| FastAPI Structure Enforcement Plugin | 111+ files need consistent patterns |

### Short-Term Implementation (Medium-High Impact)

| Agent/Plugin | Reason |
|--------------|--------|
| Backend Architecture Agent | Maintains overall code quality |
| Database Migration Safety Agent | No CI/CD migration validation |
| Audit Trail Completeness Plugin | Compliance requirement |
| Authentication Flow Plugin | Security-critical paths |

### Medium-Term Implementation (Ongoing Value)

| Agent/Plugin | Reason |
|--------------|--------|
| Frontend Page Integrity Agent | Growing Next.js codebase |
| HRIS Sync Specialist Agent | Complex multi-phase sync |
| Deletion & Refactor Risk Plugin | Safe refactoring support |
| Localization Consistency Agent | Bilingual support maintenance |

### Long-Term / As-Needed

| Agent/Plugin | Reason |
|--------------|--------|
| Safe Refactor Agent | Major refactoring projects |
| Token & Session Agent | Auth system changes |
| Test Coverage Gap Plugin | Test maturity improvement |
| Environment Configuration Plugin | DevOps improvements |

---

## Summary

This analysis identified **10 Claude Agents** and **10 Claude Plugins** specifically designed for the Employee Meal Request System. The recommendations are grounded in:

1. **Actual project patterns** (CamelModel, stateless services, Celery async)
2. **Documented conventions** (CLAUDE.md CRITICAL sections)
3. **Identified pain points** (1,954-line models.py, 111+ API files)
4. **High-risk areas** (Celery event loops, HRIS sync, schema contracts)

The priority matrix reflects immediate needs (schema enforcement, Celery patterns) while planning for ongoing code quality maintenance.
