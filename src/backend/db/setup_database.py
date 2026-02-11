"""Database setup utilities for employee-meal-request."""

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.config import settings
from db.model import User, Role, Page, UserRole, RolePermission, PagePermission
from core.security import get_password_hash

logger = logging.getLogger(__name__)


async def create_database_if_not_exists():
    """Create database if it doesn't exist (PostgreSQL)."""
    import asyncpg

    database_url = (
        settings.database.url
        or "postgresql://meal_user:meal_password@localhost:5432/postgres"
    )

    # Extract connection details
    if "+asyncpg" in database_url:
        database_url = database_url.replace("postgresql+asyncpg", "postgresql")

    try:
        # Connect to default postgres database to create our database
        postgres_url = database_url.rsplit("/", 1)[0] + "/postgres"

        conn = await asyncpg.connect(postgres_url)
        db_name = database_url.rsplit("/", 1)[-1].split("?")[0]

        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )

        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Created database: {db_name}")
        else:
            logger.info(f"Database already exists: {db_name}")

        await conn.close()

    except Exception as e:
        logger.error(f"Error creating database: {e}")


async def seed_admin_user():
    """Create default admin user if not exists."""
    from db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            # Check if admin exists
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.username == "admin"))
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                logger.info("Admin user already exists")
                return

            # Create admin user
            admin_password = settings.admin_password or "admin123"
            hashed_password = get_password_hash(admin_password)

            admin_user = User(
                id=uuid4(),
                username="admin",
                password=hashed_password,
                is_super_admin=True,
                is_active=True,
                fullname="System Administrator",
                title="Administrator",
            )

            session.add(admin_user)

            # Create admin role
            admin_role = Role(
                id=uuid4(),
                name_en="Super Admin",
                name_ar="مسؤول النظام",
                description_en="Full system access",
                description_ar="وصول كامل للنظام",
                is_active=True,
            )
            session.add(admin_role)

            await session.commit()

            # Assign role to user
            user_role = UserRole(
                id=uuid4(),
                user_id=str(admin_user.id),
                role_id=str(admin_role.id),
            )
            session.add(user_role)

            await session.commit()

            logger.info("Admin user seeded successfully")
            logger.warning(
                f"Default admin password: {admin_password} - CHANGE THIS IN PRODUCTION!"
            )

        except Exception as e:
            await session.rollback()
            logger.error(f"Error seeding admin user: {e}")


async def seed_pages():
    """Seed navigation pages hierarchy."""
    from db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            # Check if pages already exist
            from sqlalchemy import select, func

            result = await session.execute(select(func.count(Page.id)))
            count = result.scalar()

            if count > 0:
                logger.info("Pages already seeded")
                return

            # Page hierarchy for meal request system
            pages_data = [
                {
                    "name_en": "Dashboard",
                    "name_ar": "لوحة القيادة",
                    "description_en": "Main dashboard",
                    "description_ar": "اللوحة الرئيسية",
                    "icon": "LayoutDashboard",
                    "parent_id": None,
                },
                {
                    "name_en": "Meal Requests",
                    "name_ar": "طلبات الوجبات",
                    "description_en": "Manage meal requests",
                    "description_ar": "إدارة طلبات الوجبات",
                    "icon": "Utensils",
                    "parent_id": None,
                },
                {
                    "name_en": "Reports",
                    "name_ar": "التقارير",
                    "description_en": "View reports and analytics",
                    "description_ar": "عرض التقارير والتحليلات",
                    "icon": "BarChart3",
                    "parent_id": None,
                },
                {
                    "name_en": "Settings",
                    "name_ar": "الإعدادات",
                    "description_en": "System configuration",
                    "description_ar": "تكوين النظام",
                    "icon": "Settings",
                    "parent_id": None,
                },
                {
                    "name_en": "Users",
                    "name_ar": "المستخدمين",
                    "description_en": "User management",
                    "description_ar": "إدارة المستخدمين",
                    "icon": "Users",
                    "parent_id": None,
                },
                {
                    "name_en": "Roles",
                    "name_ar": "الأدوار",
                    "description_en": "Role and permission management",
                    "description_ar": "إدارة الأدوار والصلاحيات",
                    "icon": "Shield",
                    "parent_id": None,
                },
            ]

            page_map = {}

            for page_data in pages_data:
                page = Page(
                    id=uuid4(),
                    name_en=page_data["name_en"],
                    name_ar=page_data["name_ar"],
                    description_en=page_data["description_en"],
                    description_ar=page_data["description_ar"],
                    icon=page_data["icon"],
                    parent_id=page_data["parent_id"],
                    is_active=True,
                )
                session.add(page)
                page_map[page_data["name_en"]] = str(page.id)

            await session.commit()

            # Create roles for pages
            roles_data = [
                {
                    "name_en": "Requester",
                    "name_ar": "مقدم الطلب",
                    "description_en": "Can submit meal requests",
                    "description_ar": "يمكن تقديم طلبات الوجبات",
                },
                {
                    "name_en": "Manager",
                    "name_ar": "المدير",
                    "description_en": "Can approve meal requests",
                    "description_ar": "يمكن الموافقة على طلبات الوجبات",
                },
                {
                    "name_en": "Administrator",
                    "name_ar": "المسؤول",
                    "description_en": "Full system access",
                    "description_ar": "وصول كامل للنظام",
                },
            ]

            role_map = {}

            for role_data in roles_data:
                role = Role(
                    id=uuid4(),
                    name_en=role_data["name_en"],
                    name_ar=role_data["name_ar"],
                    description_en=role_data["description_en"],
                    description_ar=role_data["description_ar"],
                    is_active=True,
                )
                session.add(role)
                role_map[role_data["name_en"]] = str(role.id)

            await session.commit()

            # Grant permissions (simplified - all roles get all pages for now)
            for page_name in page_map:
                for role_name in role_map:
                    perm = PagePermission(
                        id=uuid4(),
                        role_id=int(role_map[role_name]),
                        page_id=int(page_map[page_name]),
                        is_active=True,
                    )
                    session.add(perm)

            await session.commit()

            logger.info("Pages and roles seeded successfully")

        except Exception as e:
            await session.rollback()
            logger.error(f"Error seeding pages: {e}")


async def seed_database():
    """Run all database seeding operations."""
    logger.info("Starting database seeding...")

    await seed_admin_user()
    await seed_pages()

    logger.info("Database seeding completed")


if __name__ == "__main__":
    asyncio.run(seed_database())
