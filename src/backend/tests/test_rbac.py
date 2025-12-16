"""
Tests for Role-Based Access Control (RBAC) functionality.
"""

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from utils.logging_config import setup_logging
from utils.security import create_jwt, require_role

# Setup logging for tests
setup_logging(log_level="DEBUG", enable_json_logs=False)


class TestRequireRole:
    """Test require_role dependency."""

    def test_require_role_with_admin_role(self):
        """Test require_role allows access when user has required role."""
        # Setup
        role_name = "admin"

        # Create mock payload with admin role
        mock_payload = {
            "sub": "adminuser",
            "account_id": 1,
            "roles": ["admin", "user"],
            "scopes": ["admin", "user"],
        }

        # Call require_role
        role_checker = require_role(role_name)

        # Execute
        result = role_checker(payload=mock_payload)

        # Verify
        assert result == mock_payload

    def test_require_role_with_user_role(self):
        """Test require_role allows access when user has user role."""
        # Setup
        role_name = "user"

        # Create mock payload with user role
        mock_payload = {
            "sub": "regularuser",
            "account_id": 2,
            "roles": ["user"],
            "scopes": ["user"],
        }

        # Call require_role
        role_checker = require_role(role_name)

        # Execute
        result = role_checker(payload=mock_payload)

        # Verify
        assert result == mock_payload

    def test_require_role_without_role_raises_error(self):
        """Test require_role denies access when user lacks required role."""
        # Setup
        role_name = "admin"

        # Create mock payload without admin role
        mock_payload = {
            "sub": "regularuser",
            "account_id": 2,
            "roles": ["user"],  # No admin role
            "scopes": ["user"],
        }

        # Call require_role
        role_checker = require_role(role_name)

        # Execute and verify exception
        with pytest.raises(Exception) as exc_info:  # FastAPI HTTPException
            role_checker(payload=mock_payload)

        # Verify error message
        assert "Insufficient permissions" in str(exc_info.value)
        assert "admin" in str(exc_info.value)

    def test_require_role_admin_override(self):
        """Test require_role allows access when user is admin even without specific role."""
        # Setup
        role_name = "special_role"

        # Create mock payload with admin role (should override)
        mock_payload = {
            "sub": "adminuser",
            "account_id": 1,
            "roles": ["admin"],  # Admin role should allow any role check
            "scopes": ["admin"],
        }

        # Call require_role
        role_checker = require_role(role_name)

        # Execute
        result = role_checker(payload=mock_payload)

        # Verify
        assert result == mock_payload

    def test_require_role_no_roles_raises_error(self):
        """Test require_role denies access when user has no roles."""
        # Setup
        role_name = "user"

        # Create mock payload without roles
        mock_payload = {
            "sub": "noroleuser",
            "account_id": 3,
            "roles": [],  # No roles
            "scopes": [],
        }

        # Call require_role
        role_checker = require_role(role_name)

        # Execute and verify exception
        with pytest.raises(Exception) as exc_info:  # FastAPI HTTPException
            role_checker(payload=mock_payload)

        # Verify error message
        assert "Insufficient permissions" in str(exc_info.value)


class TestRoleBasedEndpoints:
    """Test role-based access control in API endpoints."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with role-protected endpoints."""
        app = FastAPI()

        @app.get("/admin-only")
        async def admin_only_endpoint(
            payload: dict = Depends(require_role("admin")),
        ):
            return {"message": "Admin access granted", "user": payload["sub"]}

        @app.get("/user-only")
        async def user_only_endpoint(
            payload: dict = Depends(require_role("user")),
        ):
            return {"message": "User access granted", "user": payload["sub"]}

        @app.get("/any-role")
        async def any_role_endpoint(
            payload: dict = Depends(require_role("viewer")),
        ):
            return {"message": "Viewer access granted", "user": payload["sub"]}

        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    def test_admin_endpoint_with_admin_token(self, client):
        """Test admin endpoint allows access with admin token."""
        # Create admin token
        admin_payload = {
            "sub": "adminuser",
            "account_id": 1,
            "roles": ["admin", "user"],
            "scopes": ["admin", "user"],
        }
        admin_token, _ = create_jwt(
            admin_payload, "access", timedelta(minutes=15)
        )

        # Make request
        response = client.get(
            "/admin-only", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "Admin access granted" in data["message"]
        assert data["user"] == "adminuser"

    def test_admin_endpoint_with_user_token_fails(self, client):
        """Test admin endpoint denies access with user token."""
        # Create user token
        user_payload = {
            "sub": "regularuser",
            "account_id": 2,
            "roles": ["user"],
            "scopes": ["user"],
        }
        user_token, _ = create_jwt(
            user_payload, "access", timedelta(minutes=15)
        )

        # Make request
        response = client.get(
            "/admin-only", headers={"Authorization": f"Bearer {user_token}"}
        )

        # Verify
        assert response.status_code == 403  # Forbidden

    def test_user_endpoint_with_user_token(self, client):
        """Test user endpoint allows access with user token."""
        # Create user token
        user_payload = {
            "sub": "regularuser",
            "account_id": 2,
            "roles": ["user"],
            "scopes": ["user"],
        }
        user_token, _ = create_jwt(
            user_payload, "access", timedelta(minutes=15)
        )

        # Make request
        response = client.get(
            "/user-only", headers={"Authorization": f"Bearer {user_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "User access granted" in data["message"]
        assert data["user"] == "regularuser"

    def test_user_endpoint_with_admin_token(self, client):
        """Test user endpoint allows access with admin token."""
        # Create admin token
        admin_payload = {
            "sub": "adminuser",
            "account_id": 1,
            "roles": ["admin", "user"],
            "scopes": ["admin", "user"],
        }
        admin_token, _ = create_jwt(
            admin_payload, "access", timedelta(minutes=15)
        )

        # Make request
        response = client.get(
            "/user-only", headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "User access granted" in data["message"]
        assert data["user"] == "adminuser"

    def test_any_role_endpoint_with_no_matching_role(self, client):
        """Test endpoint denies access when user doesn't have the role."""
        # Create token without viewer role
        user_payload = {
            "sub": "regularuser",
            "account_id": 2,
            "roles": ["user"],  # No viewer role
            "scopes": ["user"],
        }
        user_token, _ = create_jwt(
            user_payload, "access", timedelta(minutes=15)
        )

        # Make request
        response = client.get(
            "/any-role", headers={"Authorization": f"Bearer {user_token}"}
        )

        # Verify
        assert response.status_code == 403  # Forbidden

    def test_protected_endpoint_without_token(self, client):
        """Test protected endpoint denies access without token."""
        # Make request without token
        response = client.get("/admin-only")

        # Verify
        assert response.status_code == 401  # Unauthorized


class TestRoleHierarchy:
    """Test role hierarchy and inheritance."""

    def test_admin_can_access_all_roles(self):
        """Test that admin role can access endpoints requiring any role."""
        # Setup
        admin_payload = {
            "sub": "adminuser",
            "account_id": 1,
            "roles": ["admin"],
            "scopes": ["admin"],
        }

        # Test various role requirements
        roles_to_test = ["user", "viewer", "moderator", "editor", "any_role"]

        for role in roles_to_test:
            role_checker = require_role(role)
            result = role_checker(payload=admin_payload)
            assert result == admin_payload, f"Admin should access role: {role}"

    def test_user_cannot_access_admin_only(self):
        """Test that user role cannot access admin-only endpoints."""
        # Setup
        user_payload = {
            "sub": "regularuser",
            "account_id": 2,
            "roles": ["user"],
            "scopes": ["user"],
        }

        # Test admin role requirement
        role_checker = require_role("admin")

        # Verify exception
        with pytest.raises(Exception) as exc_info:
            role_checker(payload=user_payload)

        assert "Insufficient permissions" in str(exc_info.value)


class TestTokenPayloadValidation:
    """Test token payload validation for roles."""

    def test_token_without_roles_field(self):
        """Test require_role handles tokens without roles field."""
        # Setup
        payload_without_roles = {
            "sub": "testuser",
            "account_id": 1,
            # No "roles" field
        }

        # Call require_role
        role_checker = require_role("user")

        # Execute and verify exception
        with pytest.raises(Exception) as exc_info:
            role_checker(payload=payload_without_roles)

        # Should fail because empty roles list doesn't contain "user"
        assert "Insufficient permissions" in str(exc_info.value)

    def test_token_with_none_roles(self):
        """Test require_role handles tokens with None roles field."""
        # Setup
        payload_with_none_roles = {
            "sub": "testuser",
            "account_id": 1,
            "roles": None,  # None value
        }

        # Call require_role
        role_checker = require_role("user")

        # Execute and verify exception
        with pytest.raises(Exception) as exc_info:
            role_checker(payload=payload_with_none_roles)

        assert "Insufficient permissions" in str(exc_info.value)


# Helper for creating test tokens
def create_test_token(
    username: str,
    account_id: int,
    roles: list,
    scopes: list,
    token_type: str = "access",
) -> str:
    """Helper function to create test tokens with specific roles and scopes."""
    payload = {
        "sub": username,
        "account_id": account_id,
        "roles": roles,
        "scopes": scopes,
    }
    expires_delta = timedelta(minutes=15)
    token, _ = create_jwt(payload, token_type, expires_delta)
    return token


if __name__ == "__main__":
    pytest.main([__file__])
