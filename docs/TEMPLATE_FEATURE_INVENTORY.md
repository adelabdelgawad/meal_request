# Template Repository Feature Inventory

**Document Version:** 1.0
**Date:** 2026-01-07
**Status:** Initial Discovery - Pending Review

---

## Executive Summary

This document catalogs all major features and subsystems identified in the Employee Meal Request application. Each feature is classified as either a **Template Feature** (suitable for inclusion in a generic template repository) or **System-Specific** (tightly coupled to the meal request domain).

**Repository Structure:**
- Backend: FastAPI (Python 3.x) with async/await patterns
- Frontend: Next.js 16 (React 19) with TypeScript
- Database: MariaDB (primary), SQL Server (HRIS, BioStar external)
- Cache/Broker: Redis
- Background Tasks: Celery with gevent workers

---

## Feature Inventory

---

### 1. Authentication System

**Description**
JWT-based authentication supporting dual authentication modes: LDAP/Active Directory for domain users and local password authentication for admin accounts. Includes access tokens (15min TTL) and refresh tokens (30 days TTL) with unique JTI for revocation tracking.

**Primary Paths**
- `src/backend/utils/login.py` - Login orchestration class
- `src/backend/core/security.py` - Password hashing, JWT creation/validation
- `src/backend/utils/ldap.py` - LDAP/AD authentication client
- `src/backend/utils/ad_client.py` - Async AD client with circuit breaker
- `src/backend/api/v1/auth.py` - Authentication endpoints
- `src/backend/api/v1/login.py` - Login/logout endpoints
- `src/my-app/lib/auth/` - Frontend auth utilities
- `src/my-app/app/(auth)/login/` - Login page

**Dependencies**
- Internal: User model, Session model, RevokedToken model
- External: ldap3, bonsai (async LDAP), passlib, PyJWT

**Classification**
**Template Feature**

**Rationale**
JWT authentication with access/refresh tokens is a universal pattern. The dual-mode authentication (LDAP + local) is highly reusable. LDAP-specific configuration can be made optional via environment variables.

---

### 2. Session Management

**Description**
Stateful session management with refresh token rotation, device tracking, and concurrent session limits. Sessions are stored in database with metadata (IP, user agent, fingerprint). Supports session revocation and automatic cleanup.

**Primary Paths**
- `src/backend/db/models.py` (Session model, lines 1388-1443)
- `src/backend/api/repositories/session_repository.py`
- `src/backend/api/services/revoked_token_service.py`
- `src/backend/api/v1/me.py` - User session management

**Dependencies**
- Internal: User model, RevokedToken model
- External: Redis (for session cache)

**Classification**
**Template Feature**

**Rationale**
Session management with device tracking, concurrent session limits, and revocation is common across enterprise applications. The implementation is generic and not tied to meal requests.

---

### 3. Role-Based Access Control (RBAC)

**Description**
Comprehensive RBAC system with roles, page permissions, and user-role assignments. Supports bilingual role/page names (English/Arabic). Includes page navigation permissions for dynamic menu generation.

**Primary Paths**
- `src/backend/db/models.py` (Role, PagePermission, RolePermission, Page models)
- `src/backend/api/v1/permissions.py` - Permission management endpoints
- `src/backend/api/services/role_service.py`
- `src/backend/api/services/page_service.py`
- `src/backend/api/services/page_permission_service.py`
- `src/backend/api/v1/navigation.py` - Dynamic navigation builder
- `src/my-app/app/(pages)/roles/` - Role management UI
- `src/my-app/components/navigation/` - Navigation components

**Dependencies**
- Internal: User model
- External: None

**Classification**
**Template Feature**

**Rationale**
Role-based access control with page permissions is a standard enterprise pattern. The bilingual support is a bonus feature. The navigation builder can be reused as-is.

---

### 4. User Management

**Description**
User CRUD operations with support for domain users and local accounts. Includes user source tracking (HRIS, manual), status override for HRIS sync conflict resolution, account activation/deactivation, and department assignments.

**Primary Paths**
- `src/backend/db/models.py` (User model, lines 256-388)
- `src/backend/api/v1/admin.py` - Admin user management endpoints
- `src/backend/api/services/user_service.py`
- `src/backend/api/repositories/user_repository.py`
- `src/my-app/app/(pages)/users/` - User management UI

**Dependencies**
- Internal: Role, Employee, Department, DepartmentAssignment models
- External: None

**Classification**
**Template Feature** (with modifications)

**Rationale**
User management is universal. The user source tracking and status override features are sophisticated conflict resolution mechanisms that could benefit any application integrating with external identity systems. Remove employee_id and HRIS-specific fields for template.

---

### 5. Audit Logging System

**Description**
Comprehensive audit logging with specialized log tables for different domains: authentication events, user operations, role changes, configuration changes, and replication events. Each log captures actor, action, timestamp, old/new values, and success status.

**Primary Paths**
- `src/backend/db/models.py`:
  - LogAuthentication (lines 979-1032)
  - LogMealRequest (lines 1035-1095) - **System-Specific**
  - LogUser (lines 1098-1159)
  - LogRole (lines 1162-1223)
  - LogConfiguration (lines 1226-1288)
  - LogReplication (lines 1291-1357)
  - LogPermission (lines 906-944)
  - LogMealRequestLine (lines 947-976) - **System-Specific**
- `src/backend/api/services/log_*_service.py` - Logging services
- `src/backend/api/v1/audit.py` - Audit query endpoints
- `src/my-app/app/(pages)/audit/` - Audit log viewer UI

**Dependencies**
- Internal: User model
- External: None

**Classification**
**Template Feature** (partial)

**Rationale**
Authentication, user, role, configuration, and replication audit logs are reusable. LogMealRequest and LogMealRequestLine are domain-specific and should be removed. The pattern/structure for creating domain-specific audit logs should be documented.

---

### 6. Redis Caching Layer

**Description**
Production-grade Redis integration with connection pooling, retry mechanisms, circuit breaker pattern, and comprehensive error handling. Provides cache operations, distributed locking, message queuing, and pub/sub capabilities.

**Primary Paths**
- `src/backend/core/redis.py` - Full Redis client implementation
- `src/backend/settings.py` (Redis configuration, lines 215-250)

**Dependencies**
- Internal: None
- External: redis.asyncio (aioredis)

**Classification**
**Template Feature**

**Rationale**
Redis caching with circuit breaker, distributed locking, and connection pooling is a sophisticated, reusable infrastructure component. No domain-specific logic present.

---

### 7. Background Task System (Celery)

**Description**
Celery task queue with Redis broker, gevent workers, and comprehensive task management. Includes async event loop handling pattern for database operations, retry logic with exponential backoff, and task result tracking.

**Primary Paths**
- `src/backend/celery_app.py` - Celery configuration
- `src/backend/tasks/__init__.py` - Task exports
- `src/backend/tasks/celery_bridge.py` - APScheduler-Celery bridge

**Task Files (categorized):**
- **Template:** `scheduler.py` (cleanup task pattern)
- **System-Specific:** `email.py`, `attendance.py`, `hris.py`, `domain_users.py`

**Dependencies**
- Internal: Database models, Redis
- External: Celery, gevent, kombu

**Classification**
**Template Feature** (core infrastructure)

**Rationale**
The Celery setup, `_run_async()` helper pattern, and celery_bridge are highly reusable. Domain-specific tasks (HRIS, attendance, email) should be removed but the pattern documented.

---

### 8. Job Scheduling System

**Description**
Database-backed job scheduler with APScheduler integration. Supports interval and cron schedules, distributed locking to prevent duplicate execution, execution history tracking, and a management UI.

**Primary Paths**
- `src/backend/db/models.py`:
  - TaskFunction (lines 1493-1543)
  - SchedulerJobType (lines 1581-1620)
  - SchedulerExecutionStatus (lines 1546-1578)
  - ScheduledJob (lines 1623-1786)
  - ScheduledJobExecution (lines 1789-1868)
  - ScheduledJobLock (lines 1871-1915)
  - SchedulerInstance (lines 1918-1954)
- `src/backend/api/v1/scheduler.py` - Scheduler management endpoints
- `src/backend/api/services/scheduler_service.py`
- `src/backend/utils/startup.py` - Job seeding logic
- `src/my-app/app/(pages)/scheduler/` - Scheduler management UI

**Dependencies**
- Internal: User model, Task functions
- External: APScheduler

**Classification**
**Template Feature**

**Rationale**
The scheduler framework is entirely generic. The specific task functions (HRIS sync, attendance sync) are domain-specific, but the infrastructure (models, service, UI) is fully reusable.

---

### 9. Observability System

**Description**
Production-grade observability with Prometheus metrics (HTTP, business, system, database, Celery, Redis metrics) and optional OpenTelemetry distributed tracing. Includes middleware for automatic request instrumentation.

**Primary Paths**
- `src/backend/utils/observability.py` - Full observability implementation
- `src/backend/app.py` (lines 48-49) - Initialization

**Dependencies**
- Internal: None
- External: prometheus_client, opentelemetry (optional), psutil

**Classification**
**Template Feature** (with modifications)

**Rationale**
Observability infrastructure is universally applicable. Business metrics (MEAL_REQUESTS_TOTAL, MEAL_REQUESTS_BY_STATUS, etc.) are domain-specific and should be made configurable or removed.

---

### 10. Rate Limiting

**Description**
API rate limiting using SlowAPI with Redis backend. Configurable limits for different endpoint categories (login, default, strict).

**Primary Paths**
- `src/backend/utils/security.py` - Rate limiter configuration
- `src/backend/app.py` (lines 70-71) - Rate limit registration
- `src/backend/settings.py` (lines 253-267) - Rate limit settings

**Dependencies**
- Internal: Redis
- External: slowapi

**Classification**
**Template Feature**

**Rationale**
Rate limiting is a standard security feature with no domain-specific logic.

---

### 11. Email System

**Description**
Email sending via Exchange Web Services (EWS) with async support, HTML body formatting using Jinja2 templates, and Celery task integration for background sending.

**Primary Paths**
- `src/backend/utils/mail_sender.py` - EWS email client
- `src/backend/tasks/email.py` - Email Celery tasks
- `src/backend/templates/` - Email HTML templates (domain-specific)

**Dependencies**
- Internal: Settings
- External: exchangelib, jinja2

**Classification**
**Template Feature** (infrastructure) / **System-Specific** (templates)

**Rationale**
The EmailSender class and Celery task pattern are reusable. The specific email templates (meal request notification, status update) are domain-specific and should be replaced with generic examples.

---

### 12. Settings/Configuration Management

**Description**
Pydantic Settings-based configuration with environment variable support, .env file loading, and vault integration for secrets in non-local environments.

**Primary Paths**
- `src/backend/settings.py` - All application settings
- `src/backend/.env` (example) - Environment configuration

**Dependencies**
- Internal: None
- External: pydantic-settings, python-dotenv

**Classification**
**Template Feature**

**Rationale**
Settings management is universal. Some settings are domain-specific (ATTENDANCE_SYNC_*, etc.) and should be removed or made optional.

---

### 13. Database Layer

**Description**
SQLAlchemy 2.0+ with async support using aiomysql driver. Includes multiple database connections (MariaDB primary, HRIS/BioStar external), Alembic migrations, and a CamelModel base for automatic snake_case to camelCase JSON serialization.

**Primary Paths**
- `src/backend/db/models.py` - All SQLAlchemy models
- `src/backend/db/maria_database.py` - Primary database connection
- `src/backend/db/hris_database.py` - HRIS database connection (domain-specific)
- `src/backend/api/schemas/_base.py` - CamelModel base class
- `src/backend/alembic/` - Migration management

**Dependencies**
- Internal: None
- External: SQLAlchemy, aiomysql, alembic

**Classification**
**Template Feature** (core) / **System-Specific** (external DB connections)

**Rationale**
The database setup, CamelModel pattern, and migration infrastructure are reusable. HRIS/BioStar database connections are domain-specific.

---

### 14. API Framework Patterns

**Description**
Structured API architecture with dependency injection, repository pattern, service layer, exception handlers, and standardized response schemas.

**Primary Paths**
- `src/backend/api/deps.py` - FastAPI dependencies
- `src/backend/api/exception_handlers.py` - Global exception handling
- `src/backend/api/repositories/` - Repository pattern implementations
- `src/backend/api/services/` - Business logic layer
- `src/backend/api/schemas/` - Pydantic schemas

**Dependencies**
- Internal: Database models
- External: FastAPI, Pydantic

**Classification**
**Template Feature**

**Rationale**
The architectural patterns (repository, service, dependency injection) are best practices applicable to any FastAPI application.

---

### 15. Internationalization (i18n)

**Description**
Bilingual support (English/Arabic) at model level with name_en/name_ar fields and get_name(locale) methods. Frontend uses next-intl for client-side localization.

**Primary Paths**
- `src/backend/db/models.py` - Bilingual model fields throughout
- `src/backend/settings.py` (lines 149-170) - Locale settings
- `src/my-app/` - next-intl configuration

**Dependencies**
- Internal: None
- External: next-intl

**Classification**
**Template Feature**

**Rationale**
The bilingual pattern is reusable. The specific translations are domain-specific but the infrastructure is generic.

---

### 16. Frontend Architecture

**Description**
Next.js 16 application with React 19, TypeScript, Tailwind CSS 4, Radix UI components (shadcn/ui pattern), TanStack Table for data grids, SWR for data fetching, and Zod for validation.

**Primary Paths**
- `src/my-app/app/` - App router pages
- `src/my-app/components/` - Shared components
- `src/my-app/components/ui/` - UI primitives (shadcn/ui)
- `src/my-app/components/data-table/` - Generic data table
- `src/my-app/lib/` - Utilities, hooks, API clients
- `src/my-app/lib/http/` - HTTP client with token management

**Dependencies**
- External: Next.js, React, Radix UI, TanStack Table, SWR, Zod, Tailwind CSS

**Classification**
**Template Feature** (infrastructure) / **System-Specific** (pages)

**Rationale**
The frontend architecture, UI components, data table, HTTP client, and auth utilities are reusable. Domain-specific pages (meal-request, requests, analysis) should be removed.

---

### 17. Department & Employee Management

**Description**
Hierarchical department structure with parent-child relationships, department assignments linking users to departments, and employee records synced from HRIS.

**Primary Paths**
- `src/backend/db/models.py`:
  - Department (lines 442-481)
  - DepartmentAssignment (lines 484-540)
  - Employee (lines 391-439)
- `src/backend/api/v1/departments.py`
- `src/backend/api/v1/employees.py`

**Dependencies**
- Internal: User model
- External: HRIS database

**Classification**
**Needs Review**

**Rationale**
Department hierarchy is a common organizational pattern. However, the Employee model and HRIS sync are tightly coupled to the specific domain. Consider keeping Department as template, making Employee optional.

---

### 18. Meal Request System

**Description**
Core business domain: meal request creation, approval workflow, status tracking, request lines with employee assignments, meal types configuration, and request analysis/reporting.

**Primary Paths**
- `src/backend/db/models.py`:
  - MealRequest (lines 544-617)
  - MealRequestLine (lines 621-679)
  - MealRequestLineAttendance (lines 682-751)
  - MealRequestStatus (lines 754-778)
  - MealType (lines 781-839)
- `src/backend/api/v1/meal_requests.py`
- `src/backend/api/v1/requests.py`
- `src/backend/api/v1/meal_types.py`
- `src/backend/api/v1/analysis.py`
- `src/my-app/app/(pages)/meal-request/`
- `src/my-app/app/(pages)/requests/`
- `src/my-app/app/(pages)/my-requests/`
- `src/my-app/app/(pages)/analysis/`
- `src/my-app/app/(pages)/meal-type-setup/`

**Dependencies**
- Internal: User, Employee, Department models
- External: None

**Classification**
**System-Specific**

**Rationale**
This is the core business domain unique to this application. Should NOT be included in the template.

---

### 19. HRIS Integration

**Description**
Replication of employee, department, and security user data from external HRIS (SQL Server) system. Includes user source tracking and status override for conflict resolution.

**Primary Paths**
- `src/backend/db/hris_database.py` - HRIS database connection
- `src/backend/utils/replicate_hris.py` - Replication logic
- `src/backend/tasks/hris.py` - HRIS sync Celery task
- `src/backend/api/v1/hris.py` - HRIS endpoints

**Dependencies**
- Internal: Employee, Department, SecurityUser, User models
- External: pyodbc (SQL Server)

**Classification**
**System-Specific**

**Rationale**
HRIS integration is specific to organizations using this particular HRIS system. The user source tracking pattern (Strategy A) could be documented as a best practice for external system integration.

---

### 20. Attendance Integration

**Description**
Syncing attendance data from BioStar/TMS time management system. Populates meal request line attendance times for validation.

**Primary Paths**
- `src/backend/utils/sync_attendance.py` - Attendance sync logic
- `src/backend/tasks/attendance.py` - Attendance sync Celery tasks
- `src/backend/api/services/attendance_sync_service.py`

**Dependencies**
- Internal: MealRequestLineAttendance, Employee models
- External: BioStar database (SQL Server)

**Classification**
**System-Specific**

**Rationale**
Attendance integration is specific to the meal request validation workflow and external time management system.

---

### 21. Domain User Sync

**Description**
Synchronization of Active Directory user information for caching and quick lookup without repeated AD queries.

**Primary Paths**
- `src/backend/db/models.py` (DomainUser, lines 1446-1485)
- `src/backend/tasks/domain_users.py` - Domain user sync task
- `src/backend/api/v1/domain_users.py`

**Dependencies**
- Internal: None
- External: LDAP/AD

**Classification**
**Template Feature** (with LDAP dependency)

**Rationale**
Domain user caching is useful for any application integrating with Active Directory. Should be included as optional feature.

---

### 22. Email Notifications

**Description**
Email recipient configuration with roles (admin, requester, CC recipients) for notification routing.

**Primary Paths**
- `src/backend/db/models.py`:
  - Email (lines 842-858)
  - EmailRole (lines 861-871)
- `src/backend/api/services/email_service.py`
- `src/backend/api/services/email_role_service.py`

**Dependencies**
- Internal: None
- External: None

**Classification**
**Template Feature**

**Rationale**
Email recipient/role configuration is a generic notification routing pattern.

---

### 23. Security User Model

**Description**
Tracks user accounts from external security system (HRIS), including deleted/locked status for access control decisions.

**Primary Paths**
- `src/backend/db/models.py` (SecurityUser, lines 230-252)
- `src/backend/api/services/security_user_service.py`

**Dependencies**
- Internal: Employee model
- External: HRIS

**Classification**
**System-Specific**

**Rationale**
SecurityUser is specifically for HRIS integration and access control based on external system status.

---

### 24. Internal Token Service

**Description**
Service-to-service authentication using internal JWT tokens for secure inter-service communication.

**Primary Paths**
- `src/backend/api/services/internal_token_service.py`
- `src/backend/api/v1/internal_auth.py`

**Dependencies**
- Internal: JWT configuration
- External: None

**Classification**
**Template Feature**

**Rationale**
Internal service authentication is useful for microservice architectures or secure background job triggers.

---

### 25. Docker Infrastructure

**Description**
Docker Compose configuration for local development and production deployment.

**Primary Paths**
- `docker-compose.yml` - Main compose file
- `docker/` - Docker-related configurations

**Dependencies**
- External: Docker, Docker Compose

**Classification**
**Template Feature**

**Rationale**
Docker configuration is infrastructure that needs domain-specific customization but provides a good starting point.

---

## Classification Summary

### Template Features (Include in Template)

| Feature | Modifications Needed |
|---------|---------------------|
| Authentication System | None - fully generic |
| Session Management | None - fully generic |
| RBAC System | None - fully generic |
| User Management | Remove employee_id, simplify user source |
| Audit Logging | Remove domain-specific log tables |
| Redis Caching Layer | None - fully generic |
| Background Task System | Remove domain-specific tasks, keep patterns |
| Job Scheduling System | Remove domain-specific task functions |
| Observability System | Remove domain-specific metrics |
| Rate Limiting | None - fully generic |
| Email System (infrastructure) | Replace templates with examples |
| Settings Management | Remove domain-specific settings |
| Database Layer (core) | Remove external DB connections |
| API Framework Patterns | None - fully generic |
| Internationalization | None - fully generic |
| Frontend Architecture | Remove domain-specific pages |
| Email Notifications | None - fully generic |
| Internal Token Service | None - fully generic |
| Docker Infrastructure | Update for generic use |
| Domain User Sync | Make optional (requires LDAP) |

### System-Specific Features (Exclude from Template)

| Feature | Reason |
|---------|--------|
| Meal Request System | Core business domain |
| HRIS Integration | External system specific |
| Attendance Integration | External system specific |
| Security User Model | HRIS-dependent |
| MealRequest audit logs | Domain-specific |

### Needs Review

| Feature | Decision Point |
|---------|---------------|
| Department & Employee | Keep Department, make Employee optional/example |

---

## Template Creation Rules (Draft)

### Files to Copy As-Is

1. **Core Infrastructure**
   - `src/backend/core/security.py`
   - `src/backend/core/redis.py`
   - `src/backend/api/schemas/_base.py`
   - `src/backend/api/deps.py`
   - `src/backend/api/exception_handlers.py`
   - `src/backend/celery_app.py`
   - `src/backend/alembic/env.py`

2. **Frontend Infrastructure**
   - `src/my-app/components/ui/` (all files)
   - `src/my-app/components/data-table/` (all files)
   - `src/my-app/components/navigation/` (all files)
   - `src/my-app/lib/http/`
   - `src/my-app/lib/auth/`
   - `src/my-app/lib/utils/`

3. **Configuration**
   - `docker-compose.yml` (with modifications)
   - `.env.example` (with modifications)

### Files to Recreate with Modifications

1. **Models (`src/backend/db/models.py`)**
   - Keep: Base, User, Role, Page, PagePermission, RolePermission, Session, RevokedToken, DomainUser, Email, EmailRole
   - Keep: LogAuthentication, LogUser, LogRole, LogConfiguration, LogReplication, LogPermission
   - Keep: Scheduler models (TaskFunction, ScheduledJob, etc.)
   - Remove: Employee, Department, DepartmentAssignment (or make example)
   - Remove: MealRequest, MealRequestLine, MealRequestLineAttendance, MealRequestStatus, MealType
   - Remove: SecurityUser
   - Remove: LogMealRequest, LogMealRequestLine

2. **Settings (`src/backend/settings.py`)**
   - Remove: ATTENDANCE_* settings
   - Keep: All other settings
   - Add: Placeholder for domain-specific settings section

3. **API Routers**
   - Keep: auth, login, me, navigation, permissions, admin, audit, scheduler, internal_auth, domain_users
   - Remove: meal_requests, requests, meal_types, analysis, reporting, hris, employees, departments

4. **Frontend Pages**
   - Keep: login, users, roles, audit, scheduler
   - Remove: meal-request, requests, my-requests, analysis, meal-type-setup
   - Add: Example dashboard page

5. **Celery Tasks**
   - Keep: `scheduler.py` (cleanup_history_task)
   - Keep: `celery_bridge.py`
   - Remove: `email.py`, `attendance.py`, `hris.py`, `domain_users.py`
   - Add: Example task file with pattern documentation

6. **Observability (`src/backend/utils/observability.py`)**
   - Remove: MEAL_REQUESTS_* metrics
   - Keep: HTTP, auth, database, system, Celery, Redis metrics
   - Add: Comment section for adding domain-specific metrics

### Expected Template Structure

```
template-repo/
├── src/
│   ├── backend/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── login.py
│   │   │   │   ├── me.py
│   │   │   │   ├── navigation.py
│   │   │   │   ├── permissions.py
│   │   │   │   ├── admin.py
│   │   │   │   ├── audit.py
│   │   │   │   ├── scheduler.py
│   │   │   │   └── internal_auth.py
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   ├── deps.py
│   │   │   └── exception_handlers.py
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   └── redis.py
│   │   ├── db/
│   │   │   ├── models.py (simplified)
│   │   │   └── maria_database.py
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── scheduler.py
│   │   │   ├── celery_bridge.py
│   │   │   └── example_task.py (documented pattern)
│   │   ├── utils/
│   │   │   ├── login.py
│   │   │   ├── ldap.py
│   │   │   ├── mail_sender.py
│   │   │   ├── observability.py
│   │   │   ├── startup.py
│   │   │   └── ...
│   │   ├── alembic/
│   │   ├── app.py
│   │   ├── celery_app.py
│   │   └── settings.py
│   └── my-app/
│       ├── app/
│       │   ├── (auth)/
│       │   │   └── login/
│       │   ├── (pages)/
│       │   │   ├── users/
│       │   │   ├── roles/
│       │   │   ├── audit/
│       │   │   ├── scheduler/
│       │   │   └── dashboard/ (example)
│       │   └── layout.tsx
│       ├── components/
│       │   ├── ui/
│       │   ├── data-table/
│       │   ├── navigation/
│       │   └── ...
│       └── lib/
│           ├── auth/
│           ├── http/
│           └── utils/
├── docker/
├── docker-compose.yml
├── CLAUDE.md (template-specific instructions)
└── README.md
```

---

## Notes for Human Review

1. **Department/Employee Decision**: The Department model represents common organizational hierarchy. Consider keeping it as an optional example. The Employee model is more domain-specific but could serve as a pattern for external entity integration.

2. **HRIS Sync Pattern**: The user source tracking and status override (Strategy A) pattern is sophisticated and valuable. Document this as a best practice even if the specific HRIS integration is removed.

3. **Audit Log Pattern**: The audit logging structure is excellent. Consider creating a "how to add domain-specific audit logs" guide in the template.

4. **Celery Async Pattern**: The `_run_async()` helper for handling event loops in Celery gevent workers is critical. Ensure this pattern is prominently documented in the template.

5. **Frontend Components**: The data-table component with filtering, sorting, and pagination is highly reusable. Consider documenting customization patterns.

6. **External Database Pattern**: Even though HRIS/BioStar connections are removed, the pattern for connecting to external databases should be documented as an example.

---

*This document is the initial discovery output. All classifications are preliminary and subject to revision based on stakeholder input.*
