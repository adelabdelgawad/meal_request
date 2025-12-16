"""
Comprehensive Authorization Tests

Tests the role-based access control (RBAC) system including:
- All 11 authorization dependency functions
- Super admin bypass
- Admin override
- Role-specific access (requester, ordertaker, auditor)
- Multi-role dependencies
- JWT scope validation
- 401 (unauthorized) and 403 (forbidden) responses
"""

import pytest
from datetime import timedelta
from typing import Dict, List
from unittest.mock import AsyncMock

from fastapi import HTTPException, status

from utils.security import (
    require_super_admin,
    require_admin,
    require_ordertaker,
    require_requester,
    require_auditor,
    require_requester_or_admin,
    require_ordertaker_or_admin,
    require_auditor_or_admin,
    require_ordertaker_auditor_or_admin,
    require_requester_ordertaker_or_admin,
    require_authenticated,
    create_jwt,
    decode_jwt,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    return session


def create_test_token(scopes: List[str], user_id: str = "test-user-id") -> tuple[str, str]:
    """Helper to create a test JWT token with given scopes."""
    data = {
        "user_id": user_id,
        "sub": "test_user",
        "username": "test_user",
        "scopes": scopes,
        "roles": scopes,
    }
    token, jti = create_jwt(data, "access", timedelta(minutes=15))
    return token, jti


def create_payload_with_scopes(scopes: List[str], user_id: str = "test-user-id") -> Dict:
    """Helper to create a mock JWT payload with given scopes."""
    return {
        "user_id": user_id,
        "sub": "test_user",
        "username": "test_user",
        "scopes": scopes,
        "roles": scopes,
        "jti": "test-jti-123",
        "type": "access",
    }


# ============================================================================
# Test JWT Token Creation and Validation
# ============================================================================


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_jwt_with_scopes(self):
        """Test creating JWT with role scopes."""
        data = {"user_id": "123", "sub": "testuser", "username": "testuser"}
        token, jti = create_jwt(data, "access", timedelta(minutes=15))

        assert token is not None
        assert jti is not None
        assert len(jti) == 36  # UUID format

        # Decode and verify
        payload = decode_jwt(token)
        assert payload["user_id"] == "123"
        assert payload["sub"] == "testuser"
        assert payload["jti"] == jti
        assert payload["type"] == "access"

    def test_decode_jwt_with_scopes(self):
        """Test decoding JWT and extracting scopes."""
        scopes = ["admin", "requester"]
        token, _ = create_test_token(scopes)

        payload = decode_jwt(token)
        assert "scopes" in payload
        assert set(payload["scopes"]) == set(scopes)

    def test_decode_expired_token(self):
        """Test decoding expired token raises 401."""
        data = {"user_id": "123", "sub": "testuser"}
        token, _ = create_jwt(data, "access", timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()


# ============================================================================
# Test Super Admin Access
# ============================================================================


class TestSuperAdminAccess:
    """Test super admin role has access to all endpoints."""

    @pytest.mark.asyncio
    async def test_super_admin_require_super_admin(self):
        """Super admin can access require_super_admin endpoints."""
        payload = create_payload_with_scopes(["super_admin"])
        result = await require_super_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_super_admin_require_admin(self):
        """Super admin can access require_admin endpoints."""
        payload = create_payload_with_scopes(["super_admin"])
        result = await require_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_super_admin_require_ordertaker(self):
        """Super admin can access require_ordertaker endpoints."""
        payload = create_payload_with_scopes(["super_admin"])
        result = await require_ordertaker(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_super_admin_require_requester(self):
        """Super admin can access require_requester endpoints."""
        payload = create_payload_with_scopes(["super_admin"])
        result = await require_requester(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_super_admin_require_auditor(self):
        """Super admin can access require_auditor endpoints."""
        payload = create_payload_with_scopes(["super_admin"])
        result = await require_auditor(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_non_super_admin_cannot_access_super_admin_endpoint(self):
        """Non-super-admin users cannot access require_super_admin endpoints."""
        payload = create_payload_with_scopes(["admin"])

        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Super Admin" in exc_info.value.detail


# ============================================================================
# Test Admin Access
# ============================================================================


class TestAdminAccess:
    """Test admin role access patterns."""

    @pytest.mark.asyncio
    async def test_admin_require_admin(self):
        """Admin can access require_admin endpoints."""
        payload = create_payload_with_scopes(["admin"])
        result = await require_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_admin_require_ordertaker(self):
        """Admin can access require_ordertaker endpoints (admin override)."""
        payload = create_payload_with_scopes(["admin"])
        result = await require_ordertaker(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_admin_require_requester(self):
        """Admin can access require_requester endpoints (admin override)."""
        payload = create_payload_with_scopes(["admin"])
        result = await require_requester(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_admin_require_auditor(self):
        """Admin can access require_auditor endpoints (admin override)."""
        payload = create_payload_with_scopes(["admin"])
        result = await require_auditor(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_admin_cannot_access_super_admin(self):
        """Admin CANNOT access require_super_admin endpoints."""
        payload = create_payload_with_scopes(["admin"])

        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_admin_endpoint(self):
        """Non-admin users cannot access require_admin endpoints."""
        payload = create_payload_with_scopes(["requester"])

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin" in exc_info.value.detail


# ============================================================================
# Test Role-Specific Access
# ============================================================================


class TestRoleSpecificAccess:
    """Test individual role access patterns."""

    @pytest.mark.asyncio
    async def test_ordertaker_can_access_ordertaker_endpoint(self):
        """Ordertaker can access require_ordertaker endpoints."""
        payload = create_payload_with_scopes(["ordertaker"])
        result = await require_ordertaker(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_ordertaker_cannot_access_requester_endpoint(self):
        """Ordertaker CANNOT access require_requester endpoints."""
        payload = create_payload_with_scopes(["ordertaker"])

        with pytest.raises(HTTPException) as exc_info:
            await require_requester(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_requester_can_access_requester_endpoint(self):
        """Requester can access require_requester endpoints."""
        payload = create_payload_with_scopes(["requester"])
        result = await require_requester(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_requester_cannot_access_ordertaker_endpoint(self):
        """Requester CANNOT access require_ordertaker endpoints."""
        payload = create_payload_with_scopes(["requester"])

        with pytest.raises(HTTPException) as exc_info:
            await require_ordertaker(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_auditor_can_access_auditor_endpoint(self):
        """Auditor can access require_auditor endpoints."""
        payload = create_payload_with_scopes(["auditor"])
        result = await require_auditor(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_auditor_cannot_access_ordertaker_endpoint(self):
        """Auditor CANNOT access require_ordertaker endpoints."""
        payload = create_payload_with_scopes(["auditor"])

        with pytest.raises(HTTPException) as exc_info:
            await require_ordertaker(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# Test Multi-Role Dependencies
# ============================================================================


class TestMultiRoleDependencies:
    """Test dependencies that accept multiple roles."""

    @pytest.mark.asyncio
    async def test_requester_or_admin_with_requester(self):
        """Requester can access require_requester_or_admin endpoints."""
        payload = create_payload_with_scopes(["requester"])
        result = await require_requester_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_requester_or_admin_with_admin(self):
        """Admin can access require_requester_or_admin endpoints."""
        payload = create_payload_with_scopes(["admin"])
        result = await require_requester_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_requester_or_admin_with_super_admin(self):
        """Super admin can access require_requester_or_admin endpoints."""
        payload = create_payload_with_scopes(["super_admin"])
        result = await require_requester_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_requester_or_admin_rejects_ordertaker(self):
        """Ordertaker CANNOT access require_requester_or_admin endpoints."""
        payload = create_payload_with_scopes(["ordertaker"])

        with pytest.raises(HTTPException) as exc_info:
            await require_requester_or_admin(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_ordertaker_or_admin_with_ordertaker(self):
        """Ordertaker can access require_ordertaker_or_admin endpoints."""
        payload = create_payload_with_scopes(["ordertaker"])
        result = await require_ordertaker_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_auditor_or_admin_with_auditor(self):
        """Auditor can access require_auditor_or_admin endpoints."""
        payload = create_payload_with_scopes(["auditor"])
        result = await require_auditor_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_ordertaker_auditor_or_admin_with_ordertaker(self):
        """Ordertaker can access require_ordertaker_auditor_or_admin endpoints."""
        payload = create_payload_with_scopes(["ordertaker"])
        result = await require_ordertaker_auditor_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_ordertaker_auditor_or_admin_with_auditor(self):
        """Auditor can access require_ordertaker_auditor_or_admin endpoints."""
        payload = create_payload_with_scopes(["auditor"])
        result = await require_ordertaker_auditor_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_requester_ordertaker_or_admin_with_requester(self):
        """Requester can access require_requester_ordertaker_or_admin endpoints."""
        payload = create_payload_with_scopes(["requester"])
        result = await require_requester_ordertaker_or_admin(payload)
        assert result == payload

    @pytest.mark.asyncio
    async def test_requester_ordertaker_or_admin_with_ordertaker(self):
        """Ordertaker can access require_requester_ordertaker_or_admin endpoints."""
        payload = create_payload_with_scopes(["ordertaker"])
        result = await require_requester_ordertaker_or_admin(payload)
        assert result == payload


# ============================================================================
# Test Multi-Role Users
# ============================================================================


class TestMultiRoleUsers:
    """Test users with multiple role assignments."""

    @pytest.mark.asyncio
    async def test_user_with_multiple_roles(self):
        """User with multiple roles can access endpoints requiring any of those roles."""
        payload = create_payload_with_scopes(["requester", "ordertaker"])

        # Should be able to access both
        result1 = await require_requester(payload)
        assert result1 == payload

        result2 = await require_ordertaker(payload)
        assert result2 == payload

    @pytest.mark.asyncio
    async def test_user_with_admin_and_ordertaker(self):
        """User with admin + ordertaker roles has full admin access."""
        payload = create_payload_with_scopes(["admin", "ordertaker"])

        # Admin role should provide access
        result = await require_admin(payload)
        assert result == payload

        # But still cannot access super_admin
        with pytest.raises(HTTPException):
            await require_super_admin(payload)


# ============================================================================
# Test Authentication Requirement
# ============================================================================


class TestAuthenticationRequired:
    """Test require_authenticated dependency."""

    @pytest.mark.asyncio
    async def test_authenticated_user_any_role(self):
        """Any authenticated user can access require_authenticated endpoints."""
        for role in ["requester", "ordertaker", "auditor", "admin", "super_admin"]:
            payload = create_payload_with_scopes([role])
            result = await require_authenticated(payload)
            assert result == payload

    @pytest.mark.asyncio
    async def test_authenticated_user_no_roles(self):
        """Authenticated user with no roles can still access require_authenticated endpoints."""
        payload = create_payload_with_scopes([])
        result = await require_authenticated(payload)
        assert result == payload


# ============================================================================
# Test Missing Scopes
# ============================================================================


class TestMissingScopes:
    """Test behavior when payload is missing scopes field."""

    @pytest.mark.asyncio
    async def test_missing_scopes_field(self):
        """Missing scopes field in payload should be treated as empty list."""
        payload = {
            "user_id": "test-user",
            "sub": "test_user",
            "username": "test_user",
            # No 'scopes' field
        }

        # Should fail authorization checks that require specific roles
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(payload)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_empty_scopes_list(self):
        """Empty scopes list should fail role checks but pass authenticated check."""
        payload = create_payload_with_scopes([])

        # Should fail role-specific checks
        with pytest.raises(HTTPException):
            await require_admin(payload)

        # But should pass authenticated check
        result = await require_authenticated(payload)
        assert result == payload


# ============================================================================
# Test Error Messages
# ============================================================================


class TestErrorMessages:
    """Test that error messages are clear and specific."""

    @pytest.mark.asyncio
    async def test_super_admin_error_message(self):
        """Super admin rejection provides clear error message."""
        payload = create_payload_with_scopes(["admin"])

        with pytest.raises(HTTPException) as exc_info:
            await require_super_admin(payload)

        assert "Super Admin role required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_admin_error_message(self):
        """Admin rejection provides clear error message."""
        payload = create_payload_with_scopes(["requester"])

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(payload)

        assert "Admin role required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_multi_role_error_message(self):
        """Multi-role rejection provides clear error message."""
        payload = create_payload_with_scopes(["auditor"])

        with pytest.raises(HTTPException) as exc_info:
            await require_requester_or_admin(payload)

        assert "Requester or Admin role required" in exc_info.value.detail


# ============================================================================
# Integration Tests
# ============================================================================


class TestAuthorizationIntegration:
    """Integration tests for full authorization flow."""

    @pytest.mark.asyncio
    async def test_full_authorization_hierarchy(self):
        """Test complete authorization hierarchy from super_admin down."""
        # Super admin can access everything
        super_admin_payload = create_payload_with_scopes(["super_admin"])
        assert await require_super_admin(super_admin_payload)
        assert await require_admin(super_admin_payload)
        assert await require_ordertaker(super_admin_payload)

        # Admin can access most but not super_admin
        admin_payload = create_payload_with_scopes(["admin"])
        with pytest.raises(HTTPException):
            await require_super_admin(admin_payload)
        assert await require_admin(admin_payload)
        assert await require_ordertaker(admin_payload)  # Admin override

        # Regular role can only access their specific endpoints
        ordertaker_payload = create_payload_with_scopes(["ordertaker"])
        with pytest.raises(HTTPException):
            await require_super_admin(ordertaker_payload)
        with pytest.raises(HTTPException):
            await require_admin(ordertaker_payload)
        assert await require_ordertaker(ordertaker_payload)

    @pytest.mark.asyncio
    async def test_role_isolation(self):
        """Test that roles are properly isolated from each other."""
        # Requester cannot access ordertaker endpoints
        requester = create_payload_with_scopes(["requester"])
        with pytest.raises(HTTPException):
            await require_ordertaker(requester)

        # Ordertaker cannot access requester-only endpoints (if admin override removed)
        ordertaker = create_payload_with_scopes(["ordertaker"])
        with pytest.raises(HTTPException):
            await require_requester(ordertaker)

        # Auditor cannot access requester or ordertaker endpoints
        auditor = create_payload_with_scopes(["auditor"])
        with pytest.raises(HTTPException):
            await require_requester(auditor)
        with pytest.raises(HTTPException):
            await require_ordertaker(auditor)


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
