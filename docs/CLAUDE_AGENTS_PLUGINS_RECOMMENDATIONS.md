# Claude Agents and Plugins Recommendations

This document provides grounded recommendations for Claude Agents and Plugins based on the actual architecture, patterns, and pain points identified in the Employee Meal Request application.

---

## 1. Recommended Claude Agents

### 1.1 Backend Architecture Agent

**Purpose:**
Assist with FastAPI endpoint development, service/repository implementation, and backend architectural decisions while enforcing project conventions.

**What it understands:**
- 3-layer architecture: Router → Service → Repository
- Dependency injection patterns (session passed to services)
- Domain exception hierarchy (`NotFoundError`, `ConflictError`, etc.)
- Async/await patterns with SQLAlchemy 2.0+
- PYTHONPATH requirements

**Typical tasks it would assist with:**
- Creating new API endpoints with proper response models
- Implementing service methods with audit logging
- Writing repository CRUD operations with pagination
- Adding background task handlers (FastAPI BackgroundTasks)
- Implementing circuit breaker patterns for external services

**Why this Agent improves productivity:**
- Ensures consistent layering (no business logic in repositories, no data access in routers)
- Automatically includes audit logging calls in service methods
- Generates proper error handling with domain exceptions
- Follows existing patterns for pagination, filtering, and sorting

**Type:** Execution-oriented (generates code following patterns)

---

### 1.2 Celery Task Specialist Agent

**Purpose:**
Create and modify Celery tasks with the mandatory async event loop handling pattern that prevents "Event loop is closed" errors.

**What it understands:**
- The `_run_async()` helper for gevent worker compatibility
- Database engine disposal in `finally` blocks
- Task registration in `celery_bridge.py`
- APScheduler-Celery integration patterns
- Execution status tracking via `execution_id`

**Typical tasks it would assist with:**
- Creating new background tasks (HRIS sync, email, attendance)
- Modifying existing tasks while preserving async patterns
- Adding retry logic and error handling
- Implementing task result storage
- Configuring APScheduler job triggers

**Why this Agent improves productivity:**
- The async Celery pattern is complex and error-prone
- One mistake causes runtime errors only visible in production
- Ensures database connections are properly disposed
- Maintains consistency with existing task implementations

**Type:** Execution-oriented (critical pattern enforcement)

---

### 1.3 Frontend Page Composition Agent

**Purpose:**
Scaffold and maintain Next.js pages following the server-first architecture with SWR client hydration.

**What it understands:**
- Server Component → Client Component data flow
- SWR configuration with `fallbackData` from SSR
- `_components/` organization pattern (columns, filters, modals, mobile)
- Page-specific Context providers
- URL-based filter state with searchParams
- Optimistic update patterns

**Typical tasks it would assist with:**
- Creating new list pages (server page.tsx + client data-table)
- Adding filter components with URL synchronization
- Implementing detail modals with SWR mutations
- Creating mobile card views for responsive layouts
- Adding status summary cards with click-to-filter

**Why this Agent improves productivity:**
- Page composition follows a consistent template
- Reduces boilerplate for common CRUD pages
- Ensures proper SSR data flow (no loading spinners on first paint)
- Maintains mobile responsiveness pattern

**Type:** Execution-oriented (scaffolds following templates)

---

### 1.4 Schema & Type Consistency Agent

**Purpose:**
Create and modify Pydantic schemas (backend) and TypeScript types (frontend) while ensuring end-to-end type safety and CamelCase compliance.

**What it understands:**
- `CamelModel` base class requirement (backend)
- snake_case (Python) ↔ camelCase (JSON) transformation
- Bilingual field patterns (`name_en`, `name_ar`, `description_en`, `description_ar`)
- Frontend TypeScript type definitions in `/types`
- Zod validation schemas for forms

**Typical tasks it would assist with:**
- Creating new response/request schemas
- Adding bilingual fields to existing models
- Generating TypeScript types from Pydantic schemas
- Creating Zod validation schemas for forms
- Ensuring API contracts match between frontend and backend

**Why this Agent improves productivity:**
- CamelCase violations break frontend parsing silently
- Bilingual fields require consistent naming
- Type mismatches between frontend/backend cause runtime errors
- Single source of truth for API contracts

**Type:** Advisory and execution (validates and generates)

---

### 1.5 Migration & Schema Change Agent

**Purpose:**
Assist with Alembic migrations while identifying high-risk changes and their downstream impacts.

**What it understands:**
- Alembic migration workflow (autogenerate, upgrade, downgrade)
- pymysql (sync) driver for migrations vs aiomysql (async) for app
- HRIS sync dependencies (user_source, status_override fields)
- Foreign key relationships and cascade behaviors
- Enum modifications requiring data migration

**Typical tasks it would assist with:**
- Creating migrations with proper rollback logic
- Identifying fields used by HRIS sync before modification
- Generating data migration scripts for enum changes
- Checking foreign key constraints before deletions
- Documenting migration impact on external systems

**Why this Agent improves productivity:**
- Schema changes can break HRIS sync unexpectedly
- Enum modifications require careful migration
- Rollback scripts are often forgotten
- External system dependencies are hard to track

**Type:** Advisory (analyzes impact before execution)

---

### 1.6 RBAC & Permission Agent

**Purpose:**
Manage role-based access control, page permissions, and audit logging patterns.

**What it understands:**
- `Role`, `RolePermission`, `PagePermission` model relationships
- Permission checking utilities (`require_admin`, `check_page_access`)
- Audit log services (`LogUserService`, `LogRoleService`, `LogPermissionService`)
- Frontend page access filtering based on user roles
- Navigation structure and permission-based rendering

**Why this Agent improves productivity:**
- Permission systems are complex with many touchpoints
- Audit logging must be consistent across all mutations
- Frontend and backend permissions must stay in sync
- New pages require both backend permission and frontend navigation updates

**Typical tasks it would assist with:**
- Adding new pages with proper permission setup
- Creating new roles with specific permissions
- Implementing audit logging for new operations
- Checking permission coverage across endpoints
- Updating navigation based on permission changes

**Type:** Advisory and execution (reviews and generates)

---

### 1.7 i18n & RTL Consistency Agent

**Purpose:**
Maintain bilingual support and RTL layout consistency across the application.

**What it understands:**
- Translation file structure (`locales/en/*.json`, `locales/ar/*.json`)
- `useLanguage()` hook and `t` object usage
- RTL layout patterns (flex-row-reverse, margin/padding flipping)
- Cookie-based locale persistence
- Backend locale detection and response localization

**Typical tasks it would assist with:**
- Adding translations for new UI strings
- Implementing RTL-aware component layouts
- Ensuring bilingual model fields are returned correctly
- Checking translation completeness across locales
- Converting LTR-only components to RTL-compatible

**Why this Agent improves productivity:**
- RTL bugs are easy to introduce and hard to spot
- Translation keys can be missed
- Bilingual backend fields need consistent handling
- Manual RTL testing is time-consuming

**Type:** Advisory and execution (checks and generates)

---

### 1.8 API Integration Agent

**Purpose:**
Handle the complexity of Next.js API routes proxying to the FastAPI backend.

**What it understands:**
- API route structure in `/app/api/`
- Cookie forwarding patterns (server-side)
- `serverApi` vs `clientApi` usage
- Result pattern (`{ ok: true, data } | { ok: false, error }`)
- SWR fetcher integration

**Typical tasks it would assist with:**
- Creating new API proxy routes
- Implementing proper cookie forwarding
- Handling Set-Cookie header propagation
- Creating server actions for mutations
- Setting up SWR hooks with proper typing

**Why this Agent improves productivity:**
- API proxy layer is critical for auth cookies
- Cookie handling mistakes break authentication
- Consistent error handling across all routes
- Type safety between Next.js and FastAPI

**Type:** Execution-oriented (generates consistent routes)

---

### 1.9 Observability Agent

**Purpose:**
Add and manage Prometheus metrics, structured logging, and health checks.

**What it understands:**
- Prometheus metric types (Counter, Histogram, Gauge)
- Structured logging with correlation IDs
- Health check endpoint patterns
- Grafana dashboard structure
- Alert rule configuration

**Typical tasks it would assist with:**
- Adding business metrics for new features
- Creating custom Grafana dashboards
- Implementing health checks for new dependencies
- Adding structured log context
- Configuring alerts for new metrics

**Why this Agent improves productivity:**
- Observability is often added as an afterthought
- Consistent metric naming across the codebase
- Dashboard creation is time-consuming
- Alert thresholds require domain knowledge

**Type:** Execution-oriented (generates metrics and dashboards)

---

### 1.10 Safe Refactor Agent

**Purpose:**
Analyze refactoring impact and identify all affected components before making changes.

**What it understands:**
- Cross-layer dependencies (router → service → repository)
- Frontend-backend API contracts
- Database model relationships
- External system dependencies (HRIS, BioStar)
- Test coverage for affected areas

**Typical tasks it would assist with:**
- Identifying all usages before renaming
- Checking API contract changes for breaking frontend
- Finding untested code paths affected by changes
- Mapping cascade effects of model changes
- Generating refactoring checklists

**Why this Agent improves productivity:**
- Refactoring in a layered architecture affects many files
- API changes can silently break frontend
- Database changes affect HRIS sync
- Manual impact analysis is error-prone

**Type:** Advisory (analyzes before changes)

---

## 2. Recommended Claude Plugins

### 2.1 CamelModel Schema Enforcement Plugin

**Scope:**
All Pydantic schema definitions in `api/schemas/`

**When it should activate:**
- Creating new schema classes
- Modifying existing schemas
- Adding response_model to endpoints

**What rules it would enforce:**
- All schemas MUST inherit from `CamelModel`, not `BaseModel`
- NEVER use `alias_generator` in individual schemas
- NEVER use `Field(alias="...")` for camelCase conversion
- All field names MUST be snake_case

**What mistakes it prevents:**
- Frontend parsing errors from missing camelCase conversion
- Duplicate alias configuration causing conflicts
- Inconsistent JSON field naming
- API contract violations

**Supports:** Review, generation

---

### 2.2 Celery Async Pattern Plugin

**Scope:**
All files in `tasks/` directory

**When it should activate:**
- Creating new Celery tasks
- Modifying existing async tasks
- Adding database operations to tasks

**What rules it would enforce:**
- Tasks with async operations MUST use `_run_async()` helper
- Database engines MUST be disposed in `finally` block of `_execute()`
- Result MUST be returned AFTER `finally` blocks
- Sessions MUST use `async with` pattern
- Task MUST be registered in celery bridge if scheduler-triggered

**What mistakes it prevents:**
- "Event loop is closed" runtime errors
- "Task got Future attached to a different loop" errors
- Database connection leaks
- Celery worker crashes in production

**Supports:** Review, generation

---

### 2.3 Repository Pattern Plugin

**Scope:**
Files in `api/repositories/`, `api/services/`, `api/v1/`

**When it should activate:**
- Creating new CRUD operations
- Adding business logic
- Modifying database queries

**What rules it would enforce:**
- Repositories ONLY do data access (no business logic)
- Services handle business logic and orchestration
- Routers are thin (validation, dependency injection, response)
- Sessions passed as parameters, not stored in instance
- Domain exceptions raised at appropriate layer

**What mistakes it prevents:**
- Business logic in repositories (hard to test)
- Data access in routers (violates separation)
- Session lifecycle issues
- Inconsistent error handling

**Supports:** Review

---

### 2.4 Audit Logging Completeness Plugin

**Scope:**
All service files in `api/services/`

**When it should activate:**
- Adding create/update/delete operations
- Modifying user, role, or permission entities
- Implementing sensitive operations

**What rules it would enforce:**
- All mutations MUST include audit logging call
- Audit logs MUST capture actor_id, target_id, action
- Success AND failure cases MUST be logged
- Log service called AFTER successful operation

**What mistakes it prevents:**
- Missing audit trail for compliance
- Incomplete actor/target tracking
- Unlogged failures
- Audit logs before actual operation (misleading)

**Supports:** Review

---

### 2.5 Frontend Page Structure Plugin

**Scope:**
Files in `app/(pages)/*/`

**When it should activate:**
- Creating new pages
- Adding components to pages
- Modifying page composition

**What rules it would enforce:**
- Page.tsx MUST be a Server Component (no 'use client')
- Client components go in `_components/` directory
- Initial data MUST be passed from server to client
- SWR MUST use `fallbackData` for SSR data
- Filters MUST sync with URL searchParams

**What mistakes it prevents:**
- Loading spinners on first paint (poor UX)
- Hydration mismatches
- Lost filter state on navigation
- Inconsistent page structure

**Supports:** Review, refactor

---

### 2.6 RTL Layout Safety Plugin

**Scope:**
All TSX files in `src/my-app/`

**When it should activate:**
- Adding layout components
- Using flex/grid containers
- Adding icons with text
- Creating modals/sheets

**What rules it would enforce:**
- Flex containers with directional items MUST be RTL-aware
- Icon margins MUST flip for RTL (`mr-2` → `ml-2`)
- Sheet/modal sides MUST use `side={isRtl ? "left" : "right"}`
- Text alignment MUST consider reading direction
- Border radius ONLY allowed for `rounded-full` (circles)

**What mistakes it prevents:**
- Broken Arabic layouts
- Icons on wrong side
- Modals appearing from wrong direction
- Inconsistent spacing in RTL

**Supports:** Review

---

### 2.7 Migration Risk Assessment Plugin

**Scope:**
Files in `alembic/versions/`

**When it should activate:**
- Creating new migrations
- Modifying existing migrations
- Before running `alembic upgrade`

**What rules it would enforce:**
- MUST have downgrade function for rollback
- Enum changes MUST include data migration
- Fields used by HRIS sync MUST be flagged
- Foreign key changes MUST check cascade effects
- NOT NULL additions MUST have default or data migration

**What mistakes it prevents:**
- Irreversible migrations
- HRIS sync breaking from schema changes
- Data loss from cascade deletes
- Failed migrations from constraint violations

**Supports:** Review

---

### 2.8 API Contract Consistency Plugin

**Scope:**
Backend `api/v1/` routes and frontend `lib/actions/`, `types/`

**When it should activate:**
- Adding new endpoints
- Modifying response schemas
- Creating frontend API calls

**What rules it would enforce:**
- Response model MUST be specified on endpoints
- Frontend types MUST match backend schema structure
- Breaking changes MUST be flagged
- Pagination responses MUST follow `PaginatedResponse` pattern
- Error responses MUST follow standard format

**What mistakes it prevents:**
- Frontend expecting wrong field names
- Missing pagination metadata
- Breaking changes without notice
- Inconsistent error handling

**Supports:** Review

---

### 2.9 Test Coverage Plugin

**Scope:**
All Python files in `api/`, `tasks/`, `utils/`

**When it should activate:**
- Adding new endpoints
- Creating new services
- Implementing new tasks

**What rules it would enforce:**
- New endpoints SHOULD have corresponding test
- Services with business logic SHOULD have unit tests
- Celery tasks SHOULD have integration tests
- Critical paths MUST have tests before merge

**What mistakes it prevents:**
- Untested code reaching production
- Regression in existing functionality
- Missing edge case coverage
- Broken features discovered late

**Supports:** Review

---

### 2.10 Deletion & Dependency Plugin

**Scope:**
All project files

**When it should activate:**
- Deleting files or functions
- Removing model fields
- Deprecating endpoints

**What rules it would enforce:**
- MUST check for all usages before deletion
- MUST verify no import references remain
- Database fields MUST check model relationships
- Endpoints MUST check frontend API calls
- External dependencies (HRIS) MUST be verified

**What mistakes it prevents:**
- Broken imports after deletion
- Orphaned foreign keys
- Frontend calling deleted endpoints
- HRIS sync referencing removed fields

**Supports:** Review, refactor

---

### 2.11 Session Management Plugin

**Scope:**
Files in `api/v1/`, `api/services/`

**When it should activate:**
- Using database sessions
- Creating new endpoints
- Modifying service methods

**What rules it would enforce:**
- Sessions obtained via `Depends(get_session)` only
- Sessions passed to services, not stored in instances
- One session per request lifecycle
- No session creation in services
- Proper async context manager usage

**What mistakes it prevents:**
- Session lifecycle bugs
- Multiple sessions per request
- Session leaks
- Transaction isolation issues

**Supports:** Review

---

### 2.12 HRIS Sync Safety Plugin

**Scope:**
Files in `utils/replicate_hris.py`, `tasks/hris.py`, models with `user_source`

**When it should activate:**
- Modifying HRIS sync logic
- Changing user model fields
- Adding user_source dependencies

**What rules it would enforce:**
- Manual users (`user_source='manual'`) NEVER modified by sync
- Override users (`status_override=True`) NEVER deactivated
- HRIS users ONLY modified with SecurityUser data
- Sync statistics MUST be logged
- Override changes MUST have audit trail

**What mistakes it prevents:**
- Manual users accidentally deactivated
- Override bypass failures
- Missing sync statistics
- Unaudited override changes

**Supports:** Review

---

## 3. Priority Matrix

| Priority | Agent/Plugin | Impact | Risk Mitigation |
|----------|-------------|--------|-----------------|
| **Critical** | CamelModel Schema Enforcement Plugin | High | Prevents frontend breaking |
| **Critical** | Celery Async Pattern Plugin | High | Prevents production crashes |
| **High** | Backend Architecture Agent | High | Ensures consistency |
| **High** | Repository Pattern Plugin | Medium | Maintains separation |
| **High** | Audit Logging Completeness Plugin | Medium | Compliance requirement |
| **High** | Migration Risk Assessment Plugin | High | Prevents data issues |
| **Medium** | Frontend Page Composition Agent | Medium | Reduces boilerplate |
| **Medium** | Schema & Type Consistency Agent | Medium | End-to-end type safety |
| **Medium** | RTL Layout Safety Plugin | Medium | Bilingual support |
| **Medium** | HRIS Sync Safety Plugin | High | User management |
| **Low** | Observability Agent | Medium | Nice to have |
| **Low** | i18n Consistency Agent | Low | Translation management |

---

## 4. Implementation Order Recommendation

1. **Phase 1 - Critical Enforcement**
   - CamelModel Schema Enforcement Plugin
   - Celery Async Pattern Plugin

2. **Phase 2 - Architecture Consistency**
   - Backend Architecture Agent
   - Repository Pattern Plugin
   - Session Management Plugin

3. **Phase 3 - Safety & Compliance**
   - Migration Risk Assessment Plugin
   - Audit Logging Completeness Plugin
   - HRIS Sync Safety Plugin

4. **Phase 4 - Frontend Productivity**
   - Frontend Page Composition Agent
   - RTL Layout Safety Plugin
   - API Contract Consistency Plugin

5. **Phase 5 - Quality & Observability**
   - Safe Refactor Agent
   - Test Coverage Plugin
   - Observability Agent

---

## 5. Notes

- All recommendations are based on patterns identified in the actual codebase
- Agents are designed for complex, multi-step assistance
- Plugins are designed for automated checking and enforcement
- Priority based on frequency of issues and impact of failures
- Implementation should be incremental to validate effectiveness
