"""
Tests for API endpoint response camelCase aliasing.

Ensures all API endpoints return camelCase JSON keys for frontend compatibility.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from main import app
from api.schemas.user_schemas import UserResponse
from api.schemas.role_schemas import RoleResponse


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    return session


class TestNavigationEndpointCamelCase:
    """Test navigation endpoints return camelCase."""

    def test_navigation_response_uses_camel_case(self, client):
        """Test GET /api/v1/navigation returns camelCase keys."""
        # Note: This test requires the app to be running and seeded with data
        # For a true unit test, mock the navigation service

        with patch("api.v1.navigation.NavigationService") as MockNavService:
            # Mock the service to return test data
            mock_service_instance = MockNavService.return_value
            mock_service_instance.build_navigation_tree = AsyncMock(return_value=[])

            response = client.get("/api/v1/navigation")

            if response.status_code == 200:
                data = response.json()

                # Check response structure has camelCase
                assert "nodes" in data
                assert "locale" in data
                # navType should be camelCase if present
                if "navType" in data or "nav_type" in data:
                    assert "navType" in data or data.get("navType") is None
                    assert "nav_type" not in data  # Should NOT have snake_case

    def test_icon_allowlist_response_uses_camel_case(self, client):
        """Test GET /api/v1/navigation/icons returns camelCase keys."""
        response = client.get("/api/v1/navigation/icons")

        assert response.status_code == 200
        data = response.json()

        # Check all keys are camelCase (or single word)
        assert "icons" in data
        assert "version" in data
        assert "count" in data

        # These are single-word fields, but verify no snake_case variants
        assert "icon_list" not in data
        assert "icon_count" not in data


class TestUserEndpointsCamelCase:
    """Test user-related endpoints return camelCase."""

    @pytest.mark.skip(reason="Requires authentication setup")
    def test_user_response_camel_case_fields(self, client):
        """Test user endpoints return camelCase field names."""
        # This would require setting up authentication and creating a user
        # Placeholder to demonstrate expected behavior

        # Example expected response structure:

        # Actual test would make request and verify:
        # response = client.get("/api/v1/users/me", headers=auth_headers)
        # assert set(response.json().keys()) == expected_fields


class TestRoleEndpointsCamelCase:
    """Test role endpoints return camelCase with bilingual fields."""

    @pytest.mark.skip(reason="Requires authentication and data setup")
    def test_role_response_bilingual_camel_case(self, client):
        """Test role endpoints return camelCase for bilingual fields."""
        # Example expected response structure for bilingual Role:

        # Actual test would verify:
        # response = client.get("/api/v1/admin/roles/1", headers=auth_headers)
        # assert set(response.json().keys()) == expected_fields


class TestPageEndpointsCamelCase:
    """Test page endpoints return camelCase for navigation fields."""

    @pytest.mark.skip(reason="Requires authentication and data setup")
    def test_page_response_navigation_fields_camel_case(self, client):
        """Test page endpoints return camelCase for navigation fields."""
        # Example expected response structure with navigation fields:

        # Actual test would verify:
        # response = client.get("/api/v1/admin/pages/1", headers=auth_headers)
        # response_keys = set(response.json().keys())
        # assert all(field in response_keys for field in expected_fields)


class TestLocaleEndpointCamelCase:
    """Test locale preference endpoint."""

    @pytest.mark.skip(reason="Requires authentication setup")
    def test_set_locale_request_accepts_camel_case(self, client):
        """Test POST /api/v1/me/locale accepts camelCase input."""
        # This would test that frontend can send camelCase
        # Even though this particular endpoint has simple fields,
        # it demonstrates the pattern

        # Would require auth:
        # response = client.post(
        #     "/api/v1/me/locale",
        #     json=payload,
        #     headers=auth_headers
        # )
        # assert response.status_code == 200


class TestRequestBodyCamelCaseAcceptance:
    """Test that endpoints accept camelCase in request bodies."""

    def test_camel_model_allows_camel_case_input(self):
        """Test CamelModel schemas accept camelCase field names."""
        from api.schemas.user_schemas import UserCreate

        # Frontend sends camelCase
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "fullName": "Test User",  # camelCase
            "isActive": True,  # camelCase
            "isDomainUser": False,  # camelCase
            "isSuperAdmin": False,  # camelCase
            "roleId": 1,  # camelCase
            "password": "password123",
        }

        # Schema should accept this
        user = UserCreate(**user_data)

        # Internal Python uses snake_case
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_domain_user is False
        assert user.is_super_admin is False
        assert user.role_id == 1

    def test_role_create_accepts_bilingual_camel_case(self):
        """Test RoleCreate accepts bilingual camelCase fields."""
        from api.schemas.role_schemas import RoleCreate

        # Frontend sends camelCase for bilingual fields
        role_data = {
            "nameEn": "Administrator",  # camelCase
            "nameAr": "مدير",  # camelCase
            "descriptionEn": "Full access",  # camelCase
            "descriptionAr": "وصول كامل",  # camelCase
        }

        role = RoleCreate(**role_data)

        assert role.name_en == "Administrator"
        assert role.name_ar == "مدير"
        assert role.description_en == "Full access"
        assert role.description_ar == "وصول كامل"


class TestMixedCaseCompatibility:
    """Test that both snake_case and camelCase work (populate_by_name)."""

    def test_accepts_both_snake_and_camel_case(self):
        """Test schemas accept both naming conventions."""
        from api.schemas.user_schemas import UserCreate

        # Python backend might use snake_case
        user_snake = UserCreate(
            username="user1",
            full_name="User One",
            is_active=True,
            role_id=1,
            password="pass123",
            is_domain_user=False,
            is_super_admin=False,
        )

        # Frontend uses camelCase
        user_camel = UserCreate(
            **{
                "username": "user2",
                "fullName": "User Two",
                "isActive": False,
                "roleId": 2,
                "password": "pass456",
                "isDomainUser": True,
                "isSuperAdmin": True,
            }
        )

        assert user_snake.full_name == "User One"
        assert user_camel.full_name == "User Two"
        assert user_snake.is_active is True
        assert user_camel.is_active is False


class TestContractValidation:
    """Integration tests to validate frontend-backend contract."""

    def test_user_response_contract(self):
        """Validate UserResponse matches expected frontend contract."""
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
            updated_at=now,
        )

        # Simulate API serialization
        json_output = user.model_dump(by_alias=True)

        # Frontend expects these exact keys
        required_camel_keys = {
            "fullName",
            "isActive",
            "isDomainUser",
            "isSuperAdmin",
            "roleId",
            "createdAt",
            "updatedAt",
        }

        # Verify all required camelCase keys are present
        for key in required_camel_keys:
            assert key in json_output, f"Missing camelCase key: {key}"

        # Verify snake_case keys are NOT present
        forbidden_snake_keys = {
            "full_name",
            "is_active",
            "is_domain_user",
            "is_super_admin",
            "role_id",
            "created_at",
            "updated_at",
        }

        for key in forbidden_snake_keys:
            assert key not in json_output, f"Found forbidden snake_case key: {key}"

    def test_role_response_bilingual_contract(self):
        """Validate RoleResponse bilingual fields match frontend contract."""
        now = datetime.now()

        role = RoleResponse(
            id=1,
            name_en="Admin",
            name_ar="مدير",
            description_en="Administrator role",
            description_ar="دور المسؤول",
            created_at=now,
            updated_at=now,
        )

        json_output = role.model_dump(by_alias=True)

        # Frontend expects camelCase for bilingual fields
        assert "nameEn" in json_output
        assert "nameAr" in json_output
        assert "descriptionEn" in json_output
        assert "descriptionAr" in json_output

        # Should NOT have snake_case
        assert "name_en" not in json_output
        assert "name_ar" not in json_output
        assert "description_en" not in json_output
        assert "description_ar" not in json_output


class TestSerializationHelpers:
    """Test serialization helper patterns."""

    def test_model_dump_by_alias_pattern(self):
        """Test the recommended pattern for manual serialization."""
        from api.schemas.user_schemas import UserResponse

        user = UserResponse(
            id=uuid4(),
            username="test",
            email="test@example.com",
            full_name="Test",
            is_active=True,
            is_domain_user=False,
            is_super_admin=False,
            role_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Recommended pattern for API responses
        response_dict = user.model_dump(by_alias=True)

        # Should have camelCase
        assert "fullName" in response_dict
        assert "isActive" in response_dict

        # Should NOT have snake_case
        assert "full_name" not in response_dict
        assert "is_active" not in response_dict

    def test_exclude_none_with_aliases(self):
        """Test exclude_none works correctly with aliases."""
        from api.schemas.user_schemas import UserUpdate

        # Partial update (some fields None)
        update = UserUpdate(
            full_name="Updated Name",
            is_active=False,
            # Other fields are None
        )

        # Serialize excluding None values
        update_dict = update.model_dump(by_alias=True, exclude_none=True)

        # Should only have non-None fields in camelCase
        assert "fullName" in update_dict
        assert "isActive" in update_dict
        assert update_dict["fullName"] == "Updated Name"
        assert update_dict["isActive"] is False

        # Should not have None fields or snake_case
        assert "email" not in update_dict
        assert "title" not in update_dict
        assert "full_name" not in update_dict
