"""Tests for bilingual support in Role and Page models."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.model import Role, Page
from sqlmodel import SQLModel as Base
from api.repositories.role_repository import RoleRepository
from api.repositories.page_repository import PageRepository
from api.services.role_service import RoleService
from api.services.page_service import PageService


# Test database URL (in-memory SQLite for testing)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create test database and tables."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


# Role Model Tests
@pytest.mark.asyncio
async def test_role_model_bilingual_fields():
    """Test Role model has bilingual fields."""
    role = Role(
        name_en="Administrator",
        name_ar="مدير النظام",
        description_en="System administrator role",
        description_ar="دور مدير النظام"
    )

    assert role.name_en == "Administrator"
    assert role.name_ar == "مدير النظام"
    assert role.description_en == "System administrator role"
    assert role.description_ar == "دور مدير النظام"


@pytest.mark.asyncio
async def test_role_get_name_locale():
    """Test Role.get_name() returns correct locale."""
    role = Role(
        name_en="User",
        name_ar="مستخدم",
    )

    assert role.get_name("en") == "User"
    assert role.get_name("ar") == "مستخدم"
    assert role.get_name() == "User"  # defaults to en
    assert role.get_name(None) == "User"


@pytest.mark.asyncio
async def test_role_get_description_locale():
    """Test Role.get_description() returns correct locale."""
    role = Role(
        name_en="Admin",
        name_ar="مشرف",
        description_en="Admin description",
        description_ar="وصف المشرف"
    )

    assert role.get_description("en") == "Admin description"
    assert role.get_description("ar") == "وصف المشرف"
    assert role.get_description() == "Admin description"  # defaults to en


# Page Model Tests
@pytest.mark.asyncio
async def test_page_model_bilingual_fields():
    """Test Page model has bilingual fields."""
    page = Page(
        name_en="Dashboard",
        name_ar="لوحة التحكم",
        description_en="Main dashboard page",
        description_ar="صفحة لوحة التحكم الرئيسية"
    )

    assert page.name_en == "Dashboard"
    assert page.name_ar == "لوحة التحكم"
    assert page.description_en == "Main dashboard page"
    assert page.description_ar == "صفحة لوحة التحكم الرئيسية"


@pytest.mark.asyncio
async def test_page_get_name_locale():
    """Test Page.get_name() returns correct locale."""
    page = Page(
        name_en="Settings",
        name_ar="الإعدادات",
    )

    assert page.get_name("en") == "Settings"
    assert page.get_name("ar") == "الإعدادات"
    assert page.get_name() == "Settings"  # defaults to en


# Repository Tests
@pytest.mark.asyncio
async def test_role_repository_create(test_db):
    """Test creating a role with bilingual fields."""
    repo = RoleRepository()
    role = Role(
        name_en="Manager",
        name_ar="مدير",
        description_en="Manager role",
        description_ar="دور المدير"
    )

    created_role = await repo.create(test_db, role)

    assert created_role.name_en == "Manager"
    assert created_role.name_ar == "مدير"
    assert created_role.id is not None


@pytest.mark.asyncio
async def test_role_repository_get_by_name_en(test_db):
    """Test getting role by English name."""
    repo = RoleRepository()
    role = Role(name_en="Supervisor", name_ar="مشرف")
    await repo.create(test_db, role)

    found_role = await repo.get_by_name_en(test_db, "Supervisor")
    assert found_role is not None
    assert found_role.name_en == "Supervisor"


@pytest.mark.asyncio
async def test_role_repository_get_by_name_ar(test_db):
    """Test getting role by Arabic name."""
    repo = RoleRepository()
    role = Role(name_en="Employee", name_ar="موظف")
    await repo.create(test_db, role)

    found_role = await repo.get_by_name_ar(test_db, "موظف")
    assert found_role is not None
    assert found_role.name_ar == "موظف"


@pytest.mark.asyncio
async def test_role_repository_get_by_name_with_locale(test_db):
    """Test getting role by name with locale parameter."""
    repo = RoleRepository()
    role = Role(name_en="Analyst", name_ar="محلل")
    await repo.create(test_db, role)

    # Find by English name
    found_en = await repo.get_by_name(test_db, "Analyst", locale="en")
    assert found_en is not None
    assert found_en.name_en == "Analyst"

    # Find by Arabic name
    found_ar = await repo.get_by_name(test_db, "محلل", locale="ar")
    assert found_ar is not None
    assert found_ar.name_ar == "محلل"


@pytest.mark.asyncio
async def test_page_repository_create(test_db):
    """Test creating a page with bilingual fields."""
    repo = PageRepository()
    page = Page(
        name_en="Reports",
        name_ar="التقارير",
        description_en="Reports page",
        description_ar="صفحة التقارير"
    )

    created_page = await repo.create(test_db, page)

    assert created_page.name_en == "Reports"
    assert created_page.name_ar == "التقارير"
    assert created_page.id is not None


@pytest.mark.asyncio
async def test_page_repository_get_by_name_locale(test_db):
    """Test getting page by name with locale."""
    repo = PageRepository()
    page = Page(name_en="Analytics", name_ar="التحليلات")
    await repo.create(test_db, page)

    # Find by English name
    found_en = await repo.get_by_name(test_db, "Analytics", locale="en")
    assert found_en is not None
    assert found_en.name_en == "Analytics"

    # Find by Arabic name
    found_ar = await repo.get_by_name(test_db, "التحليلات", locale="ar")
    assert found_ar is not None
    assert found_ar.name_ar == "التحليلات"


# Service Tests
@pytest.mark.asyncio
async def test_role_service_create(test_db):
    """Test RoleService creates role with bilingual fields."""
    service = RoleService()

    role = await service.create_role(
        test_db,
        name_en="Team Lead",
        name_ar="قائد الفريق",
        description_en="Team leader role",
        description_ar="دور قائد الفريق"
    )

    assert role.name_en == "Team Lead"
    assert role.name_ar == "قائد الفريق"


@pytest.mark.asyncio
async def test_page_service_create(test_db):
    """Test PageService creates page with bilingual fields."""
    service = PageService()

    page = await service.create_page(
        test_db,
        name_en="Users",
        name_ar="المستخدمون",
        description_en="User management page",
        description_ar="صفحة إدارة المستخدمين"
    )

    assert page.name_en == "Users"
    assert page.name_ar == "المستخدمون"


# Integration Tests
@pytest.mark.asyncio
async def test_role_update_with_bilingual_fields(test_db):
    """Test updating role with bilingual fields."""
    service = RoleService()

    # Create role
    role = await service.create_role(
        test_db,
        name_en="Junior",
        name_ar="مبتدئ"
    )

    # Update role
    updated = await service.update_role(
        test_db,
        role.id,
        name_en="Junior Developer",
        name_ar="مطور مبتدئ",
        description_en="Junior developer role",
        description_ar="دور مطور مبتدئ"
    )

    assert updated.name_en == "Junior Developer"
    assert updated.name_ar == "مطور مبتدئ"
    assert updated.description_en == "Junior developer role"


@pytest.mark.asyncio
async def test_page_update_with_bilingual_fields(test_db):
    """Test updating page with bilingual fields."""
    service = PageService()

    # Create page
    page = await service.create_page(
        test_db,
        name_en="Home",
        name_ar="الصفحة الرئيسية"
    )

    # Update page
    updated = await service.update_page(
        test_db,
        page.id,
        name_en="Home Page",
        name_ar="الصفحة الرئيسية المحدثة",
        description_en="Main home page",
        description_ar="الصفحة الرئيسية الأساسية"
    )

    assert updated.name_en == "Home Page"
    assert updated.name_ar == "الصفحة الرئيسية المحدثة"
    assert updated.description_en == "Main home page"


# Locale Dependency Tests
def test_get_locale_from_query_param():
    """Test get_locale() extracts locale from query parameter."""
    from api.deps import get_locale

    # Test explicit lang parameter
    locale = get_locale(accept_language=None, lang="ar")
    assert locale == "ar"

    locale = get_locale(accept_language=None, lang="en")
    assert locale == "en"


def test_get_locale_from_accept_language_header():
    """Test get_locale() extracts locale from Accept-Language header."""
    from api.deps import get_locale

    # Test Accept-Language header
    locale = get_locale(accept_language="ar-EG,ar;q=0.9,en;q=0.8", lang=None)
    assert locale == "ar"

    locale = get_locale(accept_language="en-US,en;q=0.9", lang=None)
    assert locale == "en"


def test_get_locale_defaults_to_english():
    """Test get_locale() defaults to English when no locale specified."""
    from api.deps import get_locale

    locale = get_locale(accept_language=None, lang=None)
    assert locale == "en"


def test_get_locale_query_param_takes_precedence():
    """Test lang query parameter takes precedence over Accept-Language."""
    from api.deps import get_locale

    locale = get_locale(accept_language="en-US", lang="ar")
    assert locale == "ar"
