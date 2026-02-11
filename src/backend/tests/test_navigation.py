"""Tests for navigation system: tree building, permissions, icons, and seeds."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.repositories.page_repository import PageRepository
from api.services.navigation_service import NavigationService
from db.model import Page
from sqlmodel import SQLModel as Base
from utils.icon_validation import is_valid_icon_name, is_icon_in_allowlist, validate_icon
from utils.seed_pages import _create_pages

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


# Icon Validation Tests
def test_icon_name_pattern_valid():
    """Test valid icon name patterns."""
    assert is_valid_icon_name("home")
    assert is_valid_icon_name("user-plus")
    assert is_valid_icon_name("shield_check")
    assert is_valid_icon_name("settings-2")
    assert is_valid_icon_name("A1b2-c3_d4")


def test_icon_name_pattern_invalid():
    """Test invalid icon name patterns."""
    assert not is_valid_icon_name("")
    assert not is_valid_icon_name("icon with spaces")
    assert not is_valid_icon_name("icon@special")
    assert not is_valid_icon_name("icon/slash")
    assert not is_valid_icon_name("a" * 65)  # Too long


def test_icon_in_allowlist():
    """Test icon allowlist checking."""
    assert is_icon_in_allowlist("home")
    assert is_icon_in_allowlist("settings")
    assert is_icon_in_allowlist("user")
    assert is_icon_in_allowlist("shield-check")
    assert not is_icon_in_allowlist("nonexistent-icon")
    assert not is_icon_in_allowlist("custom-icon")


def test_validate_icon():
    """Test comprehensive icon validation."""
    # Valid icons
    valid, error = validate_icon("home", require_allowlist=True)
    assert valid
    assert error is None

    # None is valid (optional field)
    valid, error = validate_icon(None, require_allowlist=True)
    assert valid
    assert error is None

    # Invalid pattern
    valid, error = validate_icon("invalid@icon", require_allowlist=True)
    assert not valid
    assert "invalid characters" in error.lower()

    # Not in allowlist
    valid, error = validate_icon("custom-icon", require_allowlist=True)
    assert not valid
    assert "not in the lucide-react allowlist" in error.lower()

    # Valid pattern but allowlist not required
    valid, error = validate_icon("custom-icon", require_allowlist=False)
    assert valid
    assert error is None


# Page Model Tests
@pytest.mark.asyncio
async def test_page_model_navigation_fields():
    """Test Page model includes all navigation fields."""
    page = Page(
        name_en="Test Page",
        name_ar="صفحة تجريبية",
        path="/test",
        parent_id=None,
        order=10,
        is_menu_group=False,
        nav_type="sidebar",
        show_in_nav=True,
        icon="home",
        key="test_page",
    )

    assert page.name_en == "Test Page"
    assert page.path == "/test"
    assert page.order == 10
    assert page.nav_type == "sidebar"
    assert page.icon == "home"
    assert page.key == "test_page"
    assert not page.is_menu_group
    assert page.show_in_nav


# Page Repository Tests
@pytest.mark.asyncio
async def test_page_repository_upsert_by_key(test_db):
    """Test page upsert by key (idempotent)."""
    repo = PageRepository()

    # Create first time
    page1 = Page(
        key="test_key",
        name_en="Original",
        name_ar="الأصلي",
        order=10,
    )
    created = await repo.upsert_by_key(test_db, page1)
    await test_db.commit()

    assert created.name_en == "Original"
    assert created.id is not None
    original_id = created.id

    # Upsert again with same key (should update)
    page2 = Page(
        key="test_key",
        name_en="Updated",
        name_ar="محدث",
        order=20,
    )
    updated = await repo.upsert_by_key(test_db, page2)
    await test_db.commit()

    assert updated.id == original_id  # Same ID
    assert updated.name_en == "Updated"
    assert updated.order == 20


@pytest.mark.asyncio
async def test_page_repository_get_navigation_pages(test_db):
    """Test fetching pages for navigation."""
    repo = PageRepository()

    # Create test pages
    page1 = Page(key="p1", name_en="Page 1", name_ar="صفحة 1", nav_type="sidebar", show_in_nav=True, order=10)
    page2 = Page(key="p2", name_en="Page 2", name_ar="صفحة 2", nav_type="sidebar", show_in_nav=False, order=20)
    page3 = Page(key="p3", name_en="Page 3", name_ar="صفحة 3", nav_type="primary", show_in_nav=True, order=30)

    test_db.add_all([page1, page2, page3])
    await test_db.commit()

    # Get all visible sidebar pages
    sidebar_pages = await repo.get_navigation_pages(test_db, nav_type="sidebar", show_in_nav_only=True)
    assert len(sidebar_pages) == 1
    assert sidebar_pages[0].key == "p1"

    # Get all visible pages
    all_visible = await repo.get_navigation_pages(test_db, show_in_nav_only=True)
    assert len(all_visible) == 2


# Seed Tests
@pytest.mark.asyncio
async def test_create_pages_seed(test_db):
    """Test _create_pages creates all default pages."""
    stats = await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()

    assert stats["created"] == 6  # Home, Settings, Users, Domain Users, Service Accounts, Roles
    assert stats["updated"] == 0
    assert stats["skipped"] == 0
    assert len(stats["errors"]) == 0

    # Verify pages were created
    repo = PageRepository()
    home = await repo.get_by_key(test_db, "home")
    assert home is not None
    assert home.name_en == "Home"
    assert home.name_ar == "الرئيسية"
    assert home.icon == "home"
    assert home.path == "/"
    assert home.order == 10

    settings = await repo.get_by_key(test_db, "settings")
    assert settings is not None
    assert settings.is_menu_group
    assert settings.icon == "settings"

    users = await repo.get_by_key(test_db, "users")
    assert users is not None
    assert users.parent_id == settings.id
    assert users.icon == "user"


@pytest.mark.asyncio
async def test_create_pages_idempotent(test_db):
    """Test _create_pages is idempotent (no duplicates on re-run)."""
    # First run
    stats1 = await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()
    assert stats1["created"] == 6

    # Second run (should skip existing)
    stats2 = await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()
    assert stats2["created"] == 0
    assert stats2["skipped"] == 6


@pytest.mark.asyncio
async def test_create_pages_hierarchy(test_db):
    """Test _create_pages creates correct parent-child hierarchy."""
    await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()

    repo = PageRepository()

    # Verify hierarchy
    settings = await repo.get_by_key(test_db, "settings")
    users = await repo.get_by_key(test_db, "users")
    domain_users = await repo.get_by_key(test_db, "domain_users")
    service_accounts = await repo.get_by_key(test_db, "service_accounts")
    roles = await repo.get_by_key(test_db, "roles")

    assert users.parent_id == settings.id
    assert domain_users.parent_id == users.id
    assert service_accounts.parent_id == users.id
    assert roles.parent_id == settings.id


# Navigation Service Tests
@pytest.mark.asyncio
async def test_navigation_service_build_tree(test_db):
    """Test NavigationService builds correct tree structure."""
    # Seed pages
    await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()

    # Build tree
    nav_service = NavigationService()
    tree = await nav_service.build_navigation_tree(
        session=test_db,
        locale="en",
        nav_type=None,  # All types
        user_id=None,
        is_super_admin=True,  # See everything
    )

    # Should have root nodes (Home, Settings potentially)
    assert len(tree) > 0

    # Find Home node
    home_node = next((n for n in tree if n.key == "home"), None)
    assert home_node is not None
    assert home_node.name == "Home"
    assert home_node.icon == "home"
    assert len(home_node.children) == 0

    # Find Settings node
    settings_node = next((n for n in tree if n.key == "settings"), None)
    if settings_node:  # May not be in primary nav
        assert settings_node.is_menu_group
        assert len(settings_node.children) >= 2  # Users, Roles at minimum


@pytest.mark.asyncio
async def test_navigation_service_localization(test_db):
    """Test NavigationService returns localized names."""
    await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()

    nav_service = NavigationService()

    # English
    tree_en = await nav_service.build_navigation_tree(
        session=test_db,
        locale="en",
        user_id=None,
        is_super_admin=True,
    )
    home_en = next((n for n in tree_en if n.key == "home"), None)
    assert home_en.name == "Home"

    # Arabic
    tree_ar = await nav_service.build_navigation_tree(
        session=test_db,
        locale="ar",
        user_id=None,
        is_super_admin=True,
    )
    home_ar = next((n for n in tree_ar if n.key == "home"), None)
    assert home_ar.name == "الرئيسية"


@pytest.mark.asyncio
async def test_navigation_service_filter_by_nav_type(test_db):
    """Test filtering navigation by nav_type."""
    await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()

    nav_service = NavigationService()

    # Primary nav (should include Home)
    tree_primary = await nav_service.build_navigation_tree(
        session=test_db,
        locale="en",
        nav_type="primary",
        user_id=None,
        is_super_admin=True,
    )
    assert any(n.key == "home" for n in tree_primary)

    # Sidebar nav (should include Settings, Users, Roles)
    tree_sidebar = await nav_service.build_navigation_tree(
        session=test_db,
        locale="en",
        nav_type="sidebar",
        user_id=None,
        is_super_admin=True,
    )
    # At least Settings or its children
    assert len(tree_sidebar) > 0


@pytest.mark.asyncio
async def test_navigation_node_to_dict(test_db):
    """Test NavigationNode serialization."""
    await _create_pages(test_db, upsert_mode="create_missing")
    await test_db.commit()

    nav_service = NavigationService()
    tree = await nav_service.build_navigation_tree(
        session=test_db,
        locale="en",
        user_id=None,
        is_super_admin=True,
    )

    home_node = next((n for n in tree if n.key == "home"), None)
    assert home_node is not None

    # Convert to dict
    home_dict = home_node.to_dict()

    assert "id" in home_dict
    assert "key" in home_dict
    assert "name_en" in home_dict
    assert "name_ar" in home_dict
    assert "name" in home_dict
    assert "icon" in home_dict
    assert "path" in home_dict
    assert "children" in home_dict
    assert isinstance(home_dict["children"], list)
