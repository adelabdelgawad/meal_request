"""
Tests for CamelModel base class and camelCase aliasing.

Ensures all schema models properly serialize to camelCase JSON for frontend compatibility.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from api.schemas._base import CamelModel
from api.schemas.user_schemas import UserResponse, UserCreate, UserUpdate
from api.schemas.role_schemas import RoleResponse, RoleCreate
from api.schemas.page_schemas import PageResponse, PageCreate


class TestCamelModelBasics:
    """Test CamelModel basic functionality."""

    def test_camel_model_generates_camel_case_aliases(self):
        """Test that CamelModel automatically generates camelCase aliases."""

        class TestModel(CamelModel):
            user_id: int
            first_name: str
            is_active: bool
            created_at: datetime

        now = datetime.now()
        model = TestModel(
            user_id=123,
            first_name="John",
            is_active=True,
            created_at=now
        )

        # Serialize with aliases (what gets sent to frontend)
        json_data = model.model_dump(by_alias=True)

        # Assert camelCase keys
        assert "userId" in json_data
        assert "firstName" in json_data
        assert "isActive" in json_data
        assert "createdAt" in json_data

        # Assert snake_case keys are NOT present
        assert "user_id" not in json_data
        assert "first_name" not in json_data
        assert "is_active" not in json_data
        assert "created_at" not in json_data

        # Assert values are correct
        assert json_data["userId"] == 123
        assert json_data["firstName"] == "John"
        assert json_data["isActive"] is True

    def test_camel_model_accepts_both_snake_and_camel_case_input(self):
        """Test populate_by_name allows both snake_case and camelCase input."""

        class TestModel(CamelModel):
            user_id: int
            first_name: str

        # Test snake_case input (Python convention)
        model1 = TestModel(user_id=1, first_name="Alice")
        assert model1.user_id == 1
        assert model1.first_name == "Alice"

        # Test camelCase input (frontend sends this)
        model2 = TestModel(**{"userId": 2, "firstName": "Bob"})
        assert model2.user_id == 2
        assert model2.first_name == "Bob"

        # Test mixed input (should work too)
        model3 = TestModel(user_id=3, **{"firstName": "Charlie"})
        assert model3.user_id == 3
        assert model3.first_name == "Charlie"

    def test_camel_model_without_by_alias_uses_snake_case(self):
        """Test that without by_alias=True, output uses snake_case."""

        class TestModel(CamelModel):
            user_id: int
            first_name: str

        model = TestModel(user_id=1, first_name="Test")

        # Default serialization (internal use)
        json_data = model.model_dump()

        assert "user_id" in json_data
        assert "first_name" in json_data
        assert "userId" not in json_data
        assert "firstName" not in json_data


class TestUserSchemas:
    """Test UserResponse schema camelCase serialization."""

    def test_user_response_camel_case_serialization(self):
        """Test UserResponse serializes with camelCase keys."""
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

        json_data = user.model_dump(by_alias=True)

        # Check all expected camelCase keys
        assert "username" in json_data  # single word, unchanged
        assert "email" in json_data  # single word, unchanged
        assert "fullName" in json_data
        assert "title" in json_data
        assert "isActive" in json_data
        assert "isDomainUser" in json_data
        assert "isSuperAdmin" in json_data
        assert "roleId" in json_data
        assert "createdAt" in json_data
        assert "updatedAt" in json_data

        # Verify no snake_case keys
        assert "full_name" not in json_data
        assert "is_active" not in json_data
        assert "is_domain_user" not in json_data
        assert "is_super_admin" not in json_data
        assert "role_id" not in json_data
        assert "created_at" not in json_data
        assert "updated_at" not in json_data

    def test_user_create_accepts_camel_case_input(self):
        """Test UserCreate can accept camelCase input from frontend."""
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "fullName": "New User",
            "title": "Developer",
            "isActive": True,
            "isDomainUser": False,
            "isSuperAdmin": False,
            "roleId": 2,
            "password": "securepassword123"
        }

        user = UserCreate(**user_data)

        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        assert user.title == "Developer"
        assert user.is_active is True
        assert user.is_domain_user is False
        assert user.is_super_admin is False
        assert user.role_id == 2
        assert user.password == "securepassword123"

    def test_user_update_partial_camel_case(self):
        """Test UserUpdate with partial camelCase fields."""
        update_data = {
            "fullName": "Updated Name",
            "isActive": False
        }

        user_update = UserUpdate(**update_data)

        assert user_update.full_name == "Updated Name"
        assert user_update.is_active is False
        assert user_update.email is None  # Not provided
        assert user_update.title is None  # Not provided


class TestRoleSchemas:
    """Test Role schemas with bilingual fields."""

    def test_role_response_camel_case_with_bilingual_fields(self):
        """Test RoleResponse camelCase serialization with bilingual fields."""
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

        json_data = role.model_dump(by_alias=True)

        # Check camelCase for bilingual fields
        assert "nameEn" in json_data
        assert "nameAr" in json_data
        assert "descriptionEn" in json_data
        assert "descriptionAr" in json_data
        assert "createdAt" in json_data
        assert "updatedAt" in json_data

        # Verify snake_case not present
        assert "name_en" not in json_data
        assert "name_ar" not in json_data
        assert "description_en" not in json_data
        assert "description_ar" not in json_data

        # Verify values
        assert json_data["nameEn"] == "Administrator"
        assert json_data["nameAr"] == "مدير"

    def test_role_create_accepts_camel_case_bilingual_input(self):
        """Test RoleCreate accepts camelCase bilingual field names."""
        role_data = {
            "nameEn": "Moderator",
            "nameAr": "مشرف",
            "descriptionEn": "Content moderation",
            "descriptionAr": "إشراف على المحتوى"
        }

        role = RoleCreate(**role_data)

        assert role.name_en == "Moderator"
        assert role.name_ar == "مشرف"
        assert role.description_en == "Content moderation"
        assert role.description_ar == "إشراف على المحتوى"


class TestPageSchemas:
    """Test Page schemas with navigation fields."""

    def test_page_response_navigation_fields_camel_case(self):
        """Test PageResponse navigation fields use camelCase."""
        now = datetime.now()

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
            key="home",
            created_at=now,
            updated_at=now
        )

        json_data = page.model_dump(by_alias=True)

        # Check navigation field camelCase
        assert "navType" in json_data
        assert "isMenuGroup" in json_data
        assert "showInNav" in json_data
        assert "openInNewTab" in json_data
        assert "parentId" in json_data

        # Verify snake_case not present
        assert "nav_type" not in json_data
        assert "is_menu_group" not in json_data
        assert "show_in_nav" not in json_data
        assert "open_in_new_tab" not in json_data
        assert "parent_id" not in json_data

        # Verify values
        assert json_data["navType"] == "primary"
        assert json_data["isMenuGroup"] is False
        assert json_data["showInNav"] is True

    def test_page_create_navigation_fields_camel_case_input(self):
        """Test PageCreate accepts camelCase navigation fields."""
        page_data = {
            "nameEn": "Settings",
            "nameAr": "الإعدادات",
            "descriptionEn": "Application settings",
            "descriptionAr": "إعدادات التطبيق",
            "path": "/settings",
            "icon": "settings",
            "navType": "sidebar",
            "order": 100,
            "isMenuGroup": True,
            "showInNav": True,
            "openInNewTab": False,
            "parentId": None,
            "key": "settings"
        }

        page = PageCreate(**page_data)

        assert page.nav_type == "sidebar"
        assert page.is_menu_group is True
        assert page.show_in_nav is True
        assert page.open_in_new_tab is False
        assert page.parent_id is None


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_optional_fields_none_values(self):
        """Test that None values in optional fields serialize correctly."""

        class TestModel(CamelModel):
            required_field: str
            optional_field: Optional[str] = None
            optional_int: Optional[int] = None

        model = TestModel(required_field="test")

        json_data = model.model_dump(by_alias=True)

        assert "requiredField" in json_data
        assert "optionalField" in json_data
        assert "optionalInt" in json_data
        assert json_data["optionalField"] is None
        assert json_data["optionalInt"] is None

    def test_exclude_none_with_aliases(self):
        """Test exclude_none works with camelCase aliases."""

        class TestModel(CamelModel):
            required_field: str
            optional_field: Optional[str] = None

        model = TestModel(required_field="test")

        json_data = model.model_dump(by_alias=True, exclude_none=True)

        assert "requiredField" in json_data
        assert "optionalField" not in json_data

    def test_nested_models_preserve_camel_case(self):
        """Test nested CamelModel instances preserve camelCase."""

        class NestedModel(CamelModel):
            nested_field: str
            nested_int: int

        class ParentModel(CamelModel):
            parent_field: str
            nested_data: NestedModel

        nested = NestedModel(nested_field="test", nested_int=42)
        parent = ParentModel(parent_field="parent", nested_data=nested)

        json_data = parent.model_dump(by_alias=True)

        assert "parentField" in json_data
        assert "nestedData" in json_data
        assert "nestedField" in json_data["nestedData"]
        assert "nestedInt" in json_data["nestedData"]
        assert json_data["nestedData"]["nestedField"] == "test"
        assert json_data["nestedData"]["nestedInt"] == 42


class TestModelConfigPreservation:
    """Test that CamelModel doesn't break existing model_config."""

    def test_from_attributes_works_with_camel_model(self):
        """Test from_attributes=True works with CamelModel."""

        class MockORM:
            """Mock ORM model."""
            def __init__(self):
                self.user_id = 123
                self.first_name = "Test"
                self.is_active = True

        class TestSchema(CamelModel):
            user_id: int
            first_name: str
            is_active: bool

            model_config = {"from_attributes": True}

        orm_obj = MockORM()
        schema = TestSchema.model_validate(orm_obj)

        assert schema.user_id == 123
        assert schema.first_name == "Test"
        assert schema.is_active is True

        # Check camelCase serialization
        json_data = schema.model_dump(by_alias=True)
        assert "userId" in json_data
        assert "firstName" in json_data
        assert "isActive" in json_data
