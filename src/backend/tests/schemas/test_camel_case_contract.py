"""
Standalone tests for camelCase API contract validation.

These tests verify frontend-backend contract without requiring app startup.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from api.schemas.user_schemas import UserResponse, UserCreate, UserUpdate
from api.schemas.role_schemas import RoleResponse, RoleCreate
from api.schemas.page_schemas import PageResponse, PageCreate


class TestFrontendBackendContract:
    """Verify API responses match frontend expectations."""

    def test_user_response_frontend_contract(self):
        """Validate UserResponse produces expected frontend JSON structure."""
        user_id = uuid4()
        now = datetime.now()

        user = UserResponse(
            id=user_id,
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            title="Engineer",
            is_active=True,
            is_domain_user=False,
            is_super_admin=False,
            role_id=1,
            created_at=now,
            updated_at=now
        )

        # Simulate API JSON serialization
        json_output = user.model_dump(by_alias=True)

        # Verify camelCase keys
        assert "fullName" in json_output
        assert "isActive" in json_output
        assert "isDomainUser" in json_output
        assert "isSuperAdmin" in json_output
        assert "roleId" in json_output
        assert "createdAt" in json_output
        assert "updatedAt" in json_output

        # Verify snake_case keys are NOT present
        assert "full_name" not in json_output
        assert "is_active" not in json_output
        assert "is_domain_user" not in json_output
        assert "is_super_admin" not in json_output
        assert "role_id" not in json_output
        assert "created_at" not in json_output
        assert "updated_at" not in json_output

    def test_role_response_bilingual_frontend_contract(self):
        """Validate RoleResponse bilingual fields use camelCase."""
        now = datetime.now()

        role = RoleResponse(
            id=1,
            name_en="Administrator",
            name_ar="مدير",
            description_en="Full system access",
            description_ar="الوصول الكامل للنظام",
            created_at=now,
            updated_at=now
        )

        json_output = role.model_dump(by_alias=True)

        # Verify camelCase for bilingual fields
        assert "nameEn" in json_output
        assert "nameAr" in json_output
        assert "descriptionEn" in json_output
        assert "descriptionAr" in json_output
        assert "createdAt" in json_output
        assert "updatedAt" in json_output

        # Verify snake_case NOT present
        assert "name_en" not in json_output
        assert "name_ar" not in json_output
        assert "description_en" not in json_output
        assert "description_ar" not in json_output
        assert "created_at" not in json_output
        assert "updated_at" not in json_output

    def test_page_response_navigation_frontend_contract(self):
        """Validate PageResponse navigation fields use camelCase."""
        datetime.now()

        page = PageResponse(
            id=1,
            name_en="Home",
            name_ar="الرئيسية",
            description_en="Home page",
            description_ar="الصفحة الرئيسية",
            path="/",
            icon="home",
            nav_type="primary",
            order=10,
            is_menu_group=False,
            show_in_nav=True,
            open_in_new_tab=False,
            parent_id=None,
            key="home"
        )

        json_output = page.model_dump(by_alias=True)

        # Verify navigation fields are camelCase
        assert "navType" in json_output
        assert "isMenuGroup" in json_output
        assert "showInNav" in json_output
        assert "openInNewTab" in json_output
        assert "parentId" in json_output

        # Verify snake_case NOT present
        assert "nav_type" not in json_output
        assert "is_menu_group" not in json_output
        assert "show_in_nav" not in json_output
        assert "open_in_new_tab" not in json_output
        assert "parent_id" not in json_output


class TestFrontendInputAcceptance:
    """Test schemas accept camelCase input from frontend."""

    def test_user_create_accepts_camel_case_from_frontend(self):
        """Frontend sends camelCase in request body."""
        # Simulate frontend POST /users request body
        frontend_payload = {
            "username": "newuser",
            "email": "new@example.com",
            "fullName": "New User",
            "title": "Developer",
            "isActive": True,
            "isDomainUser": False,
            "isSuperAdmin": False,
            "roleId": 2,
            "password": "securepass123"
        }

        # Backend should accept this
        user = UserCreate(**frontend_payload)

        # Internal Python uses snake_case
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert user.is_active is True
        assert user.is_domain_user is False
        assert user.is_super_admin is False
        assert user.role_id == 2

    def test_user_update_partial_camel_case_from_frontend(self):
        """Frontend sends partial update with camelCase."""
        frontend_payload = {
            "fullName": "Updated Name",
            "isActive": False
        }

        user_update = UserUpdate(**frontend_payload)

        assert user_update.full_name == "Updated Name"
        assert user_update.is_active is False
        # Non-provided fields are None
        assert user_update.email is None
        assert user_update.title is None

    def test_role_create_accepts_bilingual_camel_case(self):
        """Frontend sends bilingual fields in camelCase."""
        frontend_payload = {
            "nameEn": "Moderator",
            "nameAr": "مشرف",
            "descriptionEn": "Content moderation",
            "descriptionAr": "إشراف على المحتوى"
        }

        role = RoleCreate(**frontend_payload)

        assert role.name_en == "Moderator"
        assert role.name_ar == "مشرف"
        assert role.description_en == "Content moderation"
        assert role.description_ar == "إشراف على المحتوى"

    def test_page_create_accepts_navigation_camel_case(self):
        """Frontend sends navigation fields in camelCase."""
        frontend_payload = {
            "nameEn": "Dashboard",
            "nameAr": "لوحة التحكم",
            "path": "/dashboard",
            "icon": "layout-dashboard",
            "navType": "sidebar",
            "order": 20,
            "isMenuGroup": False,
            "showInNav": True,
            "openInNewTab": False,
            "key": "dashboard"
        }

        page = PageCreate(**frontend_payload)

        assert page.name_en == "Dashboard"
        assert page.nav_type == "sidebar"
        assert page.is_menu_group is False
        assert page.show_in_nav is True
        assert page.open_in_new_tab is False


class TestBidirectionalCompatibility:
    """Test snake_case (Python) and camelCase (frontend) both work."""

    def test_schema_accepts_both_naming_styles(self):
        """Verify populate_by_name allows both conventions."""
        # Python style (snake_case)
        user_python = UserCreate(
            username="user1",
            full_name="User One",
            is_active=True,
            role_id=1,
            password="password123",
            is_domain_user=False,
            is_super_admin=False
        )

        # Frontend style (camelCase)
        user_frontend = UserCreate(**{
            "username": "user2",
            "fullName": "User Two",
            "isActive": False,
            "roleId": 2,
            "password": "password456",
            "isDomainUser": True,
            "isSuperAdmin": True
        })

        # Both should work
        assert user_python.full_name == "User One"
        assert user_frontend.full_name == "User Two"

        # Both serialize to camelCase
        python_json = user_python.model_dump(by_alias=True)
        frontend_json = user_frontend.model_dump(by_alias=True)

        assert "fullName" in python_json
        assert "fullName" in frontend_json
        assert "full_name" not in python_json
        assert "full_name" not in frontend_json


class TestExcludeNone:
    """Test exclude_none works correctly with camelCase."""

    def test_partial_update_exclude_none(self):
        """PATCH requests often use exclude_none."""
        update = UserUpdate(
            full_name="Updated",
            is_active=False
        )

        # Serialize for API response, excluding None
        json_output = update.model_dump(by_alias=True, exclude_none=True)

        # Only non-None fields present
        assert "fullName" in json_output
        assert "isActive" in json_output

        # None fields excluded
        assert "email" not in json_output
        assert "title" not in json_output
        assert "roleId" not in json_output

        # No snake_case
        assert "full_name" not in json_output
        assert "is_active" not in json_output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
