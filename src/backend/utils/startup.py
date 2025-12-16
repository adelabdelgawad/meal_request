import logging
import traceback
from contextlib import asynccontextmanager

from api.services.email_role_service import EmailRoleService
from api.services.meal_type_service import MealTypeService
from api.services.page_permission_service import PagePermissionService
from api.services.page_service import PageService
from api.services.role_service import RoleService
from api.services.user_service import UserService
from db.hris_database import get_hris_session
from db.maria_database import create_tables, get_maria_session
from db.models import (PagePermission, ScheduledJob, SchedulerExecutionStatus,
                       SchedulerJobType, TaskFunction)
from db.schemas import UserCreate
from fastapi import FastAPI
from settings import settings

logger = logging.getLogger(__name__)

# Store scheduler service reference for cleanup
_scheduler_service = None

# Lifespan context to manage app startup and shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_service

    try:
        # Initialize Redis connection (if enabled)
        if settings.REDIS_ENABLED:
            await _initialize_redis()

        # Create database tables
        logger.info("Creating database tables...")
        await create_tables()
        logger.info("Database tables created successfully")

        # Initialize database sessions
        logger.info("Initializing database sessions...")
        get_hris_session()

        app_session_gen = get_maria_session()
        app_session = await app_session_gen.__anext__()
        logger.info("Database session initialized")

        # Create initial data
        logger.info("Creating initial data...")
        await create_initial_data(app_session)
        logger.info("Initial data created successfully")

        # Seed scheduler lookup tables (must be done before scheduled jobs)
        logger.info("Seeding scheduler lookup tables...")
        await _seed_task_functions(app_session)
        await _seed_job_types(app_session)
        await _seed_execution_statuses(app_session)
        await app_session.commit()
        logger.info("✓ Scheduler lookup tables seeded")

        # Seed default scheduled jobs (depends on lookup tables)
        logger.info("Seeding default scheduled jobs...")
        await _seed_default_scheduled_jobs(app_session)
        await app_session.commit()
        logger.info("✓ Default scheduled jobs seeded")

        # Initialize and start scheduler (if enabled)
        if getattr(settings, "SCHEDULER_ENABLED", True):
            logger.info("Initializing scheduler...")
            await _initialize_scheduler(app_session)
            logger.info("✓ Scheduler initialized and started")

        yield  # Lifespan continues

    except Exception as e:
        logger.error(f"Error during app startup: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        yield  # Continue app startup even if there's an error

    finally:
        # Shutdown scheduler
        if _scheduler_service:
            try:
                logger.info("Stopping scheduler...")
                async for session in get_maria_session():
                    await _scheduler_service.stop(session)
                    break
                logger.info("✓ Scheduler stopped")
            except Exception as e:
                logger.error(f"Error stopping scheduler: {e}")

        # Shutdown Redis
        await _shutdown_redis()


# Function to create initial data during app startup
async def create_initial_data(session):
    try:
        logger.info("Creating root account...")
        await _create_root_account(session)
        await session.commit()
        logger.info("✓ Root account created")
    except Exception as e:
        await session.rollback()
        logger.warning(
            f"Root account creation failed (may already exist): {e}"
        )

    try:
        logger.info("Creating roles...")
        await _create_roles(session)
        await session.commit()
        logger.info("✓ Roles created")
    except Exception as e:
        await session.rollback()
        logger.warning(f"Role creation failed (may already exist): {e}")

    try:
        logger.info("Creating web pages...")
        await _create_web_pages(session)
        await session.commit()
        logger.info("✓ Web pages created")
    except Exception as e:
        await session.rollback()
        logger.warning(f"Web page creation failed (may already exist): {e}")

    try:
        logger.info("Creating page permissions...")
        await _create_page_permission(session)
        await session.commit()
        logger.info("✓ Page permissions created")
    except Exception as e:
        await session.rollback()
        logger.warning(
            f"Page permission creation failed (may already exist): {e}"
        )

    try:
        logger.info("Creating request statuses...")
        await _create_request_statuses(session)
        await session.commit()
        logger.info("✓ Request statuses created")
    except Exception as e:
        await session.rollback()
        logger.warning(
            f"Request status creation failed (may already exist): {e}"
        )

    try:
        logger.info("Creating email roles...")
        await _create_email_roles(session)
        await session.commit()
        logger.info("✓ Email roles created")
    except Exception as e:
        await session.rollback()
        logger.warning(f"Email role creation failed (may already exist): {e}")

    try:
        logger.info("Creating meal types...")
        await _create_meal_types(session)
        await session.commit()
        logger.info("✓ Meal types created")
    except Exception as e:
        await session.rollback()
        logger.warning(f"Meal type creation failed (may already exist): {e}")

    try:
        logger.info("Seeding navigation pages...")
        await _seed_navigation_pages(session)
        await session.commit()
        logger.info("✓ Navigation pages seeded")
    except Exception as e:
        await session.rollback()
        logger.warning(
            f"Navigation pages seeding failed (may already exist): {e}"
        )


# Create root account
async def _create_root_account(session):
    """
    Create root admin account on startup.
    Password from APP_PASSWORD will be automatically hashed with bcrypt
    by UserRepository.create_account() before storage.
    """
    username = settings.APP_USERNAME
    password = settings.APP_PASSWORD

    if not username or not password:
        logger.warning(
            "APP_USERNAME or APP_PASSWORD not set in environment, skipping root account creation"
        )
        return

    logger.info(f"Creating root account with username: {username}")
    user_data = UserCreate(
        username=username,
        password=password,  # Plain password - will be hashed automatically
        full_name="System Administrator",
        title="Administrator",
        is_super_admin=True,
    )
    user_service = UserService()
    await user_service._repo.create_account(session, user_data)
    logger.info("Root account created/updated with encrypted password")


# Create default web pages
async def _create_web_pages(session):
    from db.models import Page
    from sqlalchemy import select

    page_names = [
        "MealRequestPage",
        "RequestDetailsPage",
        "RequestAnalysisDashboardPage",
        "RoleManagementPage",
        "AccountsManagementPage",
    ]
    page_service = PageService()
    for name in page_names:
        # Check if page already exists
        result = await session.execute(select(Page).where(Page.name == name))
        existing = result.scalar_one_or_none()
        if not existing:
            try:
                await page_service.create_page(session, name=name)
            except Exception:
                # Ignore if page already exists (race condition)
                pass


# Create default request statuses
async def _create_request_statuses(session):
    from db.models import MealRequestStatus
    from sqlalchemy import select

    # Define statuses with bilingual names
    statuses = [
        {"id": 1, "name_en": "Pending", "name_ar": "قيد الانتظار"},
        {"id": 2, "name_en": "Approved", "name_ar": "مقبول"},
        {"id": 3, "name_en": "Rejected", "name_ar": "مرفوض"},
        {"id": 4, "name_en": "On Progress", "name_ar": "قيد التنفيذ"},
    ]

    for status_data in statuses:
        # Check if status already exists by ID
        result = await session.execute(
            select(MealRequestStatus).where(
                MealRequestStatus.id == status_data["id"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            # Create new status with explicit ID
            status = MealRequestStatus(
                id=status_data["id"],
                name_en=status_data["name_en"],
                name_ar=status_data["name_ar"],
                is_active=True
            )
            session.add(status)
            await session.flush()
            logger.info(
                f"Created meal request status: {status_data['name_en']} (id={status_data['id']})")


# Create default email roles
async def _create_email_roles(session):
    from db.models import EmailRole
    from sqlalchemy import select

    role_names = ["Request_CC", "Confirmation_CC"]
    email_role_service = EmailRoleService()
    for name in role_names:
        # Check if email role already exists
        result = await session.execute(
            select(EmailRole).where(EmailRole.name == name)
        )
        existing = result.scalar_one_or_none()
        if not existing:
            await email_role_service.create_email_role(session, name=name)


# Create default meal types
async def _create_meal_types(session):
    from db.models import MealType
    from sqlalchemy import select

    meal_types = [
        {"name_en": "Breakfast", "name_ar": "إفطار"},
        {"name_en": "Lunch", "name_ar": "غداء"},
        {"name_en": "Dinner", "name_ar": "عشاء"},
    ]
    meal_type_service = MealTypeService()
    for meal_type_data in meal_types:
        # Check if meal type already exists (check English name)
        result = await session.execute(
            select(MealType).where(
                MealType.name_en == meal_type_data["name_en"])
        )
        existing = result.scalar_one_or_none()
        if not existing:
            await meal_type_service.create_meal_type(
                session,
                name_en=meal_type_data["name_en"],
                name_ar=meal_type_data["name_ar"],
                priority=0
            )


# Create default Roles
async def _create_roles(session):
    from db.models import Role
    from sqlalchemy import select

    # Define roles with bilingual names
    roles = [
        {"name_en": "Requester", "name_ar": "طالب الوجبة"},
        {"name_en": "RequestTaker", "name_ar": "مستلم الطلب"},
        {"name_en": "Captain", "name_ar": "قائد الفريق"},
        {"name_en": "StockControl", "name_ar": "مراقب المخزون"},
    ]
    role_service = RoleService()

    for role_data in roles:
        # Check if role already exists (by English name)
        result = await session.execute(
            select(Role).where(Role.name_en == role_data["name_en"])
        )
        existing_role = result.scalar_one_or_none()

        if not existing_role:
            await role_service.create_role(
                session,
                name_en=role_data["name_en"],
                name_ar=role_data["name_ar"],
            )


# Create default Pages Permission
async def _create_page_permission(session):
    from db.models import Page, Role, User
    from sqlalchemy import and_, select

    # Get root user for created_by_id
    root_username = settings.APP_USERNAME or "admin"
    result = await session.execute(
        select(User).where(User.username == root_username)
    )
    root_user = result.scalar_one_or_none()
    if not root_user:
        logger.warning(
            "Root user not found, skipping page permission creation"
        )
        return

    created_by_id = root_user.id

    # Get role IDs by name
    async def get_role_id(role_name: str):
        result = await session.execute(
            select(Role).where(Role.name_en == role_name)
        )
        role = result.scalar_one_or_none()
        return role.id if role else None

    # Get page IDs by name
    async def get_page_id(page_name: str):
        result = await session.execute(
            select(Page).where(Page.name == page_name)
        )
        page = result.scalar_one_or_none()
        return page.id if page else None

    # Helper to grant permission only if it doesn't exist
    async def grant_if_not_exists(role_id: str, page_id: int):
        result = await session.execute(
            select(PagePermission).where(
                and_(
                    PagePermission.role_id == role_id,
                    PagePermission.page_id == page_id,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            try:
                page_permission_service = PagePermissionService()
                await page_permission_service.grant_permission(
                    session,
                    role_id=role_id,
                    page_id=page_id,
                    created_by_id=created_by_id,
                )
            except Exception:
                # Ignore if permission already exists (race condition)
                pass

    # Requester Role's Pages
    requester_id = await get_role_id("Requester")
    meal_request_page_id = await get_page_id("MealRequestPage")
    if requester_id and meal_request_page_id:
        await grant_if_not_exists(requester_id, meal_request_page_id)

    # RequestTaker Role's Pages
    request_taker_id = await get_role_id("RequestTaker")
    request_details_page_id = await get_page_id("RequestDetailsPage")
    request_analysis_page_id = await get_page_id(
        "RequestAnalysisDashboardPage"
    )
    if request_taker_id:
        if request_details_page_id:
            await grant_if_not_exists(
                request_taker_id, request_details_page_id
            )
        if request_analysis_page_id:
            await grant_if_not_exists(
                request_taker_id, request_analysis_page_id
            )

    # Captain Role's Pages
    captain_id = await get_role_id("Captain")
    accounts_mgmt_page_id = await get_page_id("AccountsManagementPage")
    if captain_id:
        if request_details_page_id:
            await grant_if_not_exists(captain_id, request_details_page_id)
        if request_analysis_page_id:
            await grant_if_not_exists(captain_id, request_analysis_page_id)
        if accounts_mgmt_page_id:
            await grant_if_not_exists(captain_id, accounts_mgmt_page_id)

    # StockControl Role's Pages
    stock_control_id = await get_role_id("StockControl")
    if stock_control_id:
        if request_details_page_id:
            await grant_if_not_exists(
                stock_control_id, request_details_page_id
            )
        if request_analysis_page_id:
            await grant_if_not_exists(
                stock_control_id, request_analysis_page_id
            )


# Seed navigation pages with idempotent upsert
async def _seed_navigation_pages(session):
    """
    Seed default navigation pages.

    Creates/updates the following pages:
    - Request (menu group)
      - Meal Request (child of Request)
      - Requests Management (child of Request)
      - History Requests (child of Request) - User's own requests
    - Reports (menu group)
      - Analysis (child of Reports)
      - Audit (child of Reports)
    - Settings (menu group)
      - Users (child of Settings)
        - Domain Users (child of Users)
        - Service Accounts (child of Users)
      - Roles (child of Settings)
    """
    from api.repositories.page_repository import PageRepository
    from db.models import Page
    from utils.icon_validation import validate_icon

    page_repo = PageRepository()
    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    # Define seed pages with exact specifications
    seed_pages = [
        # 1. Request (menu group - parent for meal request pages)
        {
            "key": "request_management",
            "name_en": "Request",
            "name_ar": "الطلبات",
            "description_en": "Meal request management",
            "description_ar": "إدارة طلبات الوجبات",
            "path": None,
            "parent_key": None,
            "nav_type": "sidebar",
            "is_menu_group": True,
            "show_in_nav": True,
            "order": 10,
            "icon": "send",
            "open_in_new_tab": False,
        },
        # 2. Meal Request (child of Request)
        {
            "key": "meal_request",
            "name_en": "Meal Request",
            "name_ar": "طلب وجبة",
            "description_en": "Create meal requests for employees",
            "description_ar": "إنشاء طلبات الوجبات للموظفين",
            "path": "/meal-request",
            "parent_key": "request_management",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 11,
            "icon": "utensils-crossed",
            "open_in_new_tab": False,
        },
        # 3. Requests Management (child of Request)
        {
            "key": "requests",
            "name_en": "Requests",
            "name_ar": "إدارة الطلبات",
            "description_en": "View and manage meal requests",
            "description_ar": "عرض وإدارة طلبات الوجبات",
            "path": "/requests",
            "parent_key": "request_management",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 12,
            "icon": "clipboard-list",
            "open_in_new_tab": False,
        },
        # 4. My Requests (child of Request) - User's own requests
        {
            "key": "my_requests",
            "name_en": "My Requests",
            "name_ar": "طلباتي",
            "description_en": "View and track your submitted meal requests",
            "description_ar": "عرض وتتبع طلبات الوجبات المقدمة",
            "path": "/my-requests",
            "parent_key": "request_management",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 13,
            "icon": "history",
            "open_in_new_tab": False,
        },
        # 5. Reports (menu group - parent for analysis pages)
        {
            "key": "reports",
            "name_en": "Reports",
            "name_ar": "التقارير",
            "description_en": "Analytics and audit reports",
            "description_ar": "التحليلات وتقارير التدقيق",
            "path": None,
            "parent_key": None,
            "nav_type": "sidebar",
            "is_menu_group": True,
            "show_in_nav": True,
            "order": 20,
            "icon": "bar-chart",
            "open_in_new_tab": False,
        },
        # 6. Analysis (child of Reports)
        {
            "key": "analysis",
            "name_en": "Analysis",
            "name_ar": "التحليل",
            "description_en": "View meal request analytics and reports",
            "description_ar": "عرض تحليلات وتقارير طلبات الوجبات",
            "path": "/analysis",
            "parent_key": "reports",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 21,
            "icon": "bar-chart-3",
            "open_in_new_tab": False,
        },
        # 7. Audit (child of Reports)
        {
            "key": "audit",
            "name_en": "Audit",
            "name_ar": "التدقيق",
            "description_en": "Detailed audit report with attendance data",
            "description_ar": "تقرير تدقيق مفصل مع بيانات الحضور",
            "path": "/audit",
            "parent_key": "reports",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 22,
            "icon": "file-search",
            "open_in_new_tab": False,
        },
        # 8. Settings (menu group)
        {
            "key": "settings",
            "name_en": "Settings",
            "name_ar": "الإعدادات",
            "description_en": "Application configuration and administrative tools",
            "description_ar": "إعدادات التطبيق وأدوات المدير",
            "path": None,
            "parent_key": None,
            "nav_type": "sidebar",
            "is_menu_group": True,
            "show_in_nav": True,
            "order": 100,
            "icon": "settings",
            "open_in_new_tab": False,
        },
        # 9. Users (child of Settings)
        {
            "key": "users",
            "name_en": "Users",
            "name_ar": "المستخدمون",
            "description_en": "Manage user accounts, access and authentication",
            "description_ar": "إدارة حسابات المستخدمين والصلاحيات والمصادقة",
            "path": "/settings/users",
            "parent_key": "settings",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 110,
            "icon": "user",
            "open_in_new_tab": False,
        },
        # 10. Domain Users (child of Users)
        {
            "key": "domain_users",
            "name_en": "Domain Users",
            "name_ar": "مستخدمي النطاق",
            "description_en": "Directory-synced domain user accounts",
            "description_ar": "حسابات المستخدمين المتزامنة مع الدليل",
            "path": "/settings/users/domain",
            "parent_key": "users",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 111,
            "icon": "users",
            "open_in_new_tab": False,
        },
        # 11. Service Accounts (child of Users)
        {
            "key": "service_accounts",
            "name_en": "Service Accounts",
            "name_ar": "حسابات الخدمة",
            "description_en": "Machine/service identities and API clients",
            "description_ar": "هويات الآلات / الخدمات وعميلات API",
            "path": "/settings/users/service-accounts",
            "parent_key": "users",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 112,
            "icon": "cpu",
            "open_in_new_tab": False,
        },
        # 12. Roles (child of Settings)
        {
            "key": "roles",
            "name_en": "Roles",
            "name_ar": "الأدوار",
            "description_en": "Role-based access control definitions and assignments",
            "description_ar": "تعريفات وصلاحيات الأدوار وتعييناتها",
            "path": "/settings/roles",
            "parent_key": "settings",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 120,
            "icon": "shield-check",
            "open_in_new_tab": False,
        },
        # 13. Scheduler (child of Settings)
        {
            "key": "scheduler",
            "name_en": "Scheduler",
            "name_ar": "المجدول",
            "description_en": "Manage scheduled tasks and background jobs",
            "description_ar": "إدارة المهام المجدولة والمهام الخلفية",
            "path": "/scheduler",
            "parent_key": "settings",
            "nav_type": "sidebar",
            "is_menu_group": False,
            "show_in_nav": True,
            "order": 130,
            "icon": "timer",
            "open_in_new_tab": False,
        },
    ]

    # First pass: Create/update pages without parent_id (to establish IDs)
    page_map = {}  # Map key -> Page object

    try:
        # Create pages in order (parents first)
        for page_data in seed_pages:
            key = page_data["key"]

            # Validate icon
            is_valid, error_msg = validate_icon(
                page_data["icon"], require_allowlist=True
            )
            if not is_valid:
                logger.warning(f"Invalid icon for page '{key}': {error_msg}")
                stats["errors"].append(f"{key}: {error_msg}")
                continue

            # Check if page exists
            existing = await page_repo.get_by_key(session, key)

            if existing:
                # Skip existing pages (safe mode)
                logger.debug(f"Skipping existing page: {key}")
                stats["skipped"] += 1
                page_map[key] = existing
                continue

            # Create new page
            page = Page()
            stats["created"] += 1

            # Set basic fields
            page.key = page_data["key"]
            page.name_en = page_data["name_en"]
            page.name_ar = page_data["name_ar"]
            page.description_en = page_data["description_en"]
            page.description_ar = page_data["description_ar"]
            page.path = page_data["path"]
            page.nav_type = page_data["nav_type"]
            page.is_menu_group = page_data["is_menu_group"]
            page.show_in_nav = page_data["show_in_nav"]
            page.order = page_data["order"]
            page.icon = page_data["icon"]
            page.open_in_new_tab = page_data["open_in_new_tab"]

            # Don't set parent_id yet (will do in second pass)
            page.parent_id = None

            session.add(page)
            await session.flush()  # Get ID assigned
            page_map[key] = page

            logger.info(f"Created page: {key} (id={page.id})")

        # Second pass: Set parent_id relationships
        for page_data in seed_pages:
            key = page_data["key"]
            parent_key = page_data.get("parent_key")

            if parent_key and key in page_map and parent_key in page_map:
                page = page_map[key]
                parent = page_map[parent_key]
                page.parent_id = parent.id
                logger.debug(
                    f"Set parent for {key}: {parent_key} (id={parent.id})"
                )

        # Final flush to save parent relationships
        await session.flush()

        logger.info(
            f"Navigation pages seeded: {stats['created']} created, "
            f"{stats['updated']} updated, {stats['skipped']} skipped"
        )

        if stats["errors"]:
            logger.warning(
                f"Encountered {len(stats['errors'])} errors during seeding:"
            )
            for error in stats["errors"]:
                logger.warning(f"  - {error}")

    except Exception as e:
        logger.error(f"Failed to seed pages: {e}")
        raise


# Seed task functions lookup table
async def _seed_task_functions(session):
    """
    Seed predefined task functions.

    Creates the following task functions if they don't exist:
    - hris_replication: HRIS data sync
    - attendance_sync: Attendance data sync
    - history_cleanup: Execution history cleanup
    - data_cleanup: General data cleanup
    - report_generation: Scheduled reports
    """
    from sqlalchemy import select

    default_task_functions = [
        {
            "key": "hris_replication",
            "function_path": "replicate.main",
            "name_en": "HRIS Data Replication",
            "name_ar": "تكرار بيانات HRIS",
            "description_en": "Replicate employee and department data from HRIS",
            "description_ar": "تكرار بيانات الموظفين والأقسام من نظام الموارد البشرية",
        },
        {
            "key": "attendance_sync",
            "function_path": "utils.sync_attendance.run_attendance_sync",
            "name_en": "Attendance Sync",
            "name_ar": "مزامنة الحضور",
            "description_en": "Synchronize attendance data from TMS system",
            "description_ar": "مزامنة بيانات الحضور من نظام إدارة الوقت",
        },
        {
            "key": "domain_user_sync",
            "function_path": "tasks.domain_users.sync_domain_users",
            "name_en": "Domain User Sync",
            "name_ar": "مزامنة مستخدمي النطاق",
            "description_en": "Synchronize domain users from Active Directory/LDAP",
            "description_ar": "مزامنة مستخدمي النطاق من خادم Active Directory/LDAP",
        },
        {
            "key": "history_cleanup",
            "function_path": "api.services.scheduler_service.cleanup_history_job",
            "name_en": "Execution History Cleanup",
            "name_ar": "تنظيف سجل التنفيذ",
            "description_en": "Clean up old execution logs and expired data",
            "description_ar": "تنظيف سجلات التنفيذ القديمة والبيانات المنتهية",
        },
        {
            "key": "data_cleanup",
            "function_path": "utils.cleanup.run_data_cleanup",
            "name_en": "Data Cleanup",
            "name_ar": "تنظيف البيانات",
            "description_en": "Clean up old execution logs and expired data",
            "description_ar": "تنظيف سجلات التنفيذ القديمة والبيانات المنتهية",
        },
        {
            "key": "report_generation",
            "function_path": "utils.reports.generate_daily_report",
            "name_en": "Report Generation",
            "name_ar": "إنشاء التقارير",
            "description_en": "Generate scheduled reports",
            "description_ar": "إنشاء التقارير المجدولة",
        },
    ]

    stats = {"created": 0, "skipped": 0}

    for tf_data in default_task_functions:
        try:
            result = await session.execute(
                select(TaskFunction).where(TaskFunction.key == tf_data["key"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                stats["skipped"] += 1
                continue

            task_function = TaskFunction(
                key=tf_data["key"],
                function_path=tf_data["function_path"],
                name_en=tf_data["name_en"],
                name_ar=tf_data["name_ar"],
                description_en=tf_data.get("description_en"),
                description_ar=tf_data.get("description_ar"),
                is_active=True,
            )
            session.add(task_function)
            await session.flush()
            stats["created"] += 1
            logger.debug(f"Created task function: {tf_data['key']}")

        except Exception as e:
            logger.warning(
                f"Failed to create task function {tf_data['key']}: {e}")

    logger.info(
        f"Task functions seeded: {stats['created']} created, {stats['skipped']} skipped"
    )


# Seed job types lookup table
async def _seed_job_types(session):
    """
    Seed predefined job types.

    Creates: interval, cron
    """
    from sqlalchemy import select

    default_job_types = [
        {
            "code": "interval",
            "name_en": "Interval",
            "name_ar": "فترة",
            "description_en": "Run job at fixed time intervals",
            "description_ar": "تشغيل المهمة على فترات زمنية ثابتة",
            "sort_order": 1,
        },
        {
            "code": "cron",
            "name_en": "Cron",
            "name_ar": "كرون",
            "description_en": "Run job based on cron schedule expression",
            "description_ar": "تشغيل المهمة بناءً على تعبير جدولة كرون",
            "sort_order": 2,
        },
    ]

    stats = {"created": 0, "skipped": 0}

    for jt_data in default_job_types:
        try:
            result = await session.execute(
                select(SchedulerJobType).where(
                    SchedulerJobType.code == jt_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                stats["skipped"] += 1
                continue

            job_type = SchedulerJobType(
                code=jt_data["code"],
                name_en=jt_data["name_en"],
                name_ar=jt_data["name_ar"],
                description_en=jt_data.get("description_en"),
                description_ar=jt_data.get("description_ar"),
                sort_order=jt_data.get("sort_order", 0),
                is_active=True,
            )
            session.add(job_type)
            await session.flush()
            stats["created"] += 1
            logger.debug(f"Created job type: {jt_data['code']}")

        except Exception as e:
            logger.warning(f"Failed to create job type {jt_data['code']}: {e}")

    logger.info(
        f"Job types seeded: {stats['created']} created, {stats['skipped']} skipped"
    )


# Seed execution statuses lookup table
async def _seed_execution_statuses(session):
    """
    Seed predefined execution statuses.

    Creates: pending, running, success, failed
    """
    from sqlalchemy import select

    default_statuses = [
        {
            "code": "pending",
            "name_en": "Pending",
            "name_ar": "قيد الانتظار",
            "sort_order": 1,
        },
        {
            "code": "running",
            "name_en": "Running",
            "name_ar": "قيد التشغيل",
            "sort_order": 2,
        },
        {
            "code": "success",
            "name_en": "Success",
            "name_ar": "نجاح",
            "sort_order": 3,
        },
        {
            "code": "failed",
            "name_en": "Failed",
            "name_ar": "فشل",
            "sort_order": 4,
        },
    ]

    stats = {"created": 0, "skipped": 0}

    for status_data in default_statuses:
        try:
            result = await session.execute(
                select(SchedulerExecutionStatus).where(
                    SchedulerExecutionStatus.code == status_data["code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                stats["skipped"] += 1
                continue

            execution_status = SchedulerExecutionStatus(
                code=status_data["code"],
                name_en=status_data["name_en"],
                name_ar=status_data["name_ar"],
                sort_order=status_data.get("sort_order", 0),
                is_active=True,
            )
            session.add(execution_status)
            await session.flush()
            stats["created"] += 1
            logger.debug(f"Created execution status: {status_data['code']}")

        except Exception as e:
            logger.warning(
                f"Failed to create execution status {status_data['code']}: {e}")

    logger.info(
        f"Execution statuses seeded: {stats['created']} created, {stats['skipped']} skipped"
    )


# Seed default scheduled jobs
async def _seed_default_scheduled_jobs(session):
    """
    Seed default scheduled jobs using FK-based structure.

    Creates the following jobs if they don't exist:
    - HRIS Data Replication (hourly)
    - Attendance Sync (every 4 hours)
    - Execution History Cleanup (daily at 2 AM)

    Requires lookup tables (task_function, job_type) to be seeded first.
    """
    from sqlalchemy import select

    # Get task function IDs
    async def get_task_function_id(key: str) -> int | None:
        result = await session.execute(
            select(TaskFunction).where(TaskFunction.key == key)
        )
        tf = result.scalar_one_or_none()
        return tf.id if tf else None

    # Get job type IDs
    async def get_job_type_id(code: str) -> int | None:
        result = await session.execute(
            select(SchedulerJobType).where(SchedulerJobType.code == code)
        )
        jt = result.scalar_one_or_none()
        return jt.id if jt else None

    # Get job type IDs once
    interval_job_type_id = await get_job_type_id("interval")
    cron_job_type_id = await get_job_type_id("cron")

    if not interval_job_type_id or not cron_job_type_id:
        logger.warning("Job types not found, skipping scheduled jobs seeding")
        return

    default_jobs = [
        {
            "task_function_key": "hris_replication",
            "job_type_code": "interval",
            "interval_hours": 1,
            "priority": 10,
            "is_enabled": True,
            "is_primary": True,
        },
        {
            "task_function_key": "attendance_sync",
            "job_type_code": "interval",
            "interval_minutes": getattr(settings, "ATTENDANCE_SYNC_INTERVAL_MINUTES", 240),
            "priority": 5,
            "is_enabled": getattr(settings, "ATTENDANCE_SYNC_ENABLED", True),
            "is_primary": True,
        },
        {
            "task_function_key": "domain_user_sync",
            "job_type_code": "cron",
            "cron_expression": "0 0 * * *",  # 12 AM midnight daily
            "priority": 3,
            "is_enabled": True,
            "is_primary": True,
        },
        {
            "task_function_key": "domain_user_sync",
            "job_type_code": "cron",
            "cron_expression": "0 12 * * *",  # 12 PM noon daily
            "priority": 3,
            "is_enabled": True,
            "is_primary": True,
        },
        {
            "task_function_key": "history_cleanup",
            "job_type_code": "cron",
            "cron_expression": "0 2 * * *",  # 2 AM daily
            "priority": 1,
            "is_enabled": True,
            "is_primary": True,
        },
    ]

    stats = {"created": 0, "updated": 0, "skipped": 0}

    for job_data in default_jobs:
        try:
            # Get task function ID
            task_function_id = await get_task_function_id(job_data["task_function_key"])
            if not task_function_id:
                logger.warning(
                    f"Task function '{job_data['task_function_key']}' not found, skipping job"
                )
                continue

            # Get job type ID
            job_type_id = (
                interval_job_type_id
                if job_data["job_type_code"] == "interval"
                else cron_job_type_id
            )

            # Check if job already exists (by task_function_id)
            result = await session.execute(
                select(ScheduledJob).where(
                    ScheduledJob.task_function_id == task_function_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update is_primary flag on existing jobs if needed
                if job_data.get("is_primary", False) and not existing.is_primary:
                    existing.is_primary = True
                    await session.flush()
                    stats["updated"] += 1
                    logger.info(
                        f"Updated is_primary for job: {job_data['task_function_key']}"
                    )
                else:
                    stats["skipped"] += 1
                    logger.debug(
                        f"Skipping existing job: {job_data['task_function_key']}"
                    )
                continue

            # Create new job using FK references
            job = ScheduledJob(
                task_function_id=task_function_id,
                job_type_id=job_type_id,
                interval_seconds=job_data.get("interval_seconds"),
                interval_minutes=job_data.get("interval_minutes"),
                interval_hours=job_data.get("interval_hours"),
                interval_days=job_data.get("interval_days"),
                cron_expression=job_data.get("cron_expression"),
                priority=job_data.get("priority", 0),
                is_enabled=job_data.get("is_enabled", True),
                is_primary=job_data.get("is_primary", False),
            )
            session.add(job)
            await session.flush()
            stats["created"] += 1
            logger.info(
                f"Created scheduled job: {job_data['task_function_key']}")

        except Exception as e:
            logger.warning(
                f"Failed to create job {job_data['task_function_key']}: {e}"
            )

    logger.info(
        f"Scheduled jobs seeded: {stats['created']} created, "
        f"{stats['updated']} updated, {stats['skipped']} skipped"
    )


# Initialize and start the scheduler
async def _initialize_scheduler(session):
    """
    Initialize and start the APScheduler service.

    Registers job functions and starts the scheduler in embedded mode.
    """
    global _scheduler_service

    from api.services.scheduler_service import get_scheduler_service

    _scheduler_service = get_scheduler_service()

    # Register known job functions
    try:
        from replicate import main as hris_replicate
        _scheduler_service.register_job_function(
            "hris_replication", hris_replicate)
    except ImportError:
        logger.warning("Could not import hris_replicate function")

    try:
        from utils.sync_attendance import run_attendance_sync
        _scheduler_service.register_job_function(
            "attendance_sync", run_attendance_sync)
    except ImportError:
        logger.warning("Could not import run_attendance_sync function")

    try:
        from tasks.domain_users import sync_domain_users
        _scheduler_service.register_job_function(
            "domain_user_sync", sync_domain_users)
    except ImportError:
        logger.warning("Could not import sync_domain_users function")

    try:
        from api.services.scheduler_service import cleanup_history_job
        _scheduler_service.register_job_function(
            "history_cleanup", cleanup_history_job)
    except ImportError:
        logger.warning("Could not import cleanup_history_job function")

    # Initialize and start
    await _scheduler_service.initialize(session, mode="embedded", instance_name="fastapi-main")

    # Ensure Celery tasks are properly initialized when Celery is enabled
    if settings.CELERY_ENABLED:
        try:
            from tasks.celery_bridge import initialize_celery_tasks
            initialize_celery_tasks()
            logger.info("✓ Celery tasks initialized during scheduler startup")
        except ImportError as e:
            logger.warning(
                f"⚠ Celery tasks not available during scheduler startup: {e}")
        except Exception as e:
            logger.error(
                f"❌ Failed to initialize Celery tasks during scheduler startup: {e}")

    await _scheduler_service.start(session)
    await session.commit()


# ============================================================================
# Redis Initialization
# ============================================================================

async def _initialize_redis() -> None:
    """
    Initialize Redis connection for caching and rate limiting.

    Called during app startup when REDIS_ENABLED=True.
    Graceful degradation: logs warning but continues if Redis unavailable.
    """
    from core.redis import init_redis, redis_health_check

    try:
        logger.info("Initializing Redis connection...")
        await init_redis(
            redis_url=settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )

        # Verify connection with health check
        health = await redis_health_check()
        if health["status"] == "healthy":
            logger.info(
                f"✓ Redis connected (version: {health.get('redis_version', 'unknown')}, "
                f"latency: {health.get('latency_ms', 'N/A')}ms)"
            )
        else:
            logger.warning(
                f"Redis health check failed: {health.get('error', 'unknown')}")

    except ConnectionError as e:
        logger.warning(
            f"Redis connection failed: {e}. "
            "Falling back to in-memory rate limiting and database-only token checks."
        )
    except Exception as e:
        logger.warning(
            f"Redis initialization error: {e}. "
            "Continuing without Redis caching."
        )


async def _shutdown_redis() -> None:
    """
    Close Redis connection during app shutdown.

    Safe to call even if Redis was never initialized.
    """
    from core.redis import close_redis, is_redis_available

    if is_redis_available():
        try:
            logger.info("Closing Redis connection...")
            await close_redis()
            logger.info("✓ Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
