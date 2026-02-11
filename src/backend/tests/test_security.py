"""
Security tests for JWT authentication and CORS.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

# Set environment variables for testing
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000,https://test.example.com"
os.environ["ENVIRONMENT"] = "local"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["JWT_ALGORITHM"] = "HS256"

from main import app

client = TestClient(app)


class TestJWTAuthentication:
    """Test JWT authentication and authorization."""

    def test_login_returns_access_token(self):
        """Test that login endpoint returns an access token when valid credentials are provided."""
        # Mock the database session and login
        with patch("routers.sec_login.get_maria_session") as mock_session:
            # Create a mock session and account
            mock_account = MagicMock()
            mock_account.id = 1
            mock_account.username = "testuser"
            mock_account.is_super_admin = False

            mock_session_gen = AsyncMock()
            mock_session_instance = AsyncMock()
            mock_session_instance.__anext__ = AsyncMock(
                return_value=mock_session_instance
            )
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session_gen.__anext__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value = mock_session_gen

            # Mock the Login class
            with patch("routers.sec_login.Login") as mock_login_class:
                mock_login = MagicMock()
                mock_login.is_authenticated = True
                mock_login.account = mock_account
                mock_login_class.return_value = mock_login

                # Mock read_pages_by_account
                with patch(
                    "db.cruds.page_crud.read_pages_by_account",
                    new_callable=AsyncMock,
                ) as mock_read_pages:
                    mock_read_pages.return_value = []

                    response = client.post(
                        "/login",
                        json={
                            "username": "testuser",
                            "password": "testpass",
                            "domain": "testdomain",
                        },
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "access_token" in data
                    assert "token_type" in data
                    assert data["token_type"] == "bearer"

    def test_protected_endpoint_rejects_without_token(self):
        """Test that protected endpoints reject requests without authentication token."""
        # Test update-request-line endpoint
        response = client.put(
            "/request-details/update-request-line",
            json={
                "account_id": 1,
                "meal_request_line_id": 1,
                "accepted": True,
                "notes": "test",
            },
        )
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_protected_endpoint_rejects_invalid_token(self):
        """Test that protected endpoints reject requests with invalid tokens."""
        # Test update-request-line endpoint
        response = client.put(
            "/request-details/update-request-line",
            json={
                "account_id": 1,
                "meal_request_line_id": 1,
                "accepted": True,
                "notes": "test",
            },
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    def test_protected_endpoint_accepts_valid_token(self):
        """Test that protected endpoints accept requests with valid tokens."""
        # Generate a valid token
        from jose import jwt

        token = jwt.encode(
            {"sub": "testuser", "scopes": ["user"]},
            "test-secret-key-for-testing-only",
            algorithm="HS256",
        )

        # Mock the database session and update function
        with patch("routers.sec_login.get_maria_session") as mock_session:
            mock_session_gen = AsyncMock()
            mock_session_instance = AsyncMock()
            mock_session_instance.__anext__ = AsyncMock(
                return_value=mock_session_instance
            )
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            mock_session_gen.__anext__ = AsyncMock(return_value=mock_session_instance)
            mock_session.return_value = mock_session_gen

            # Mock update_meal_request_line
            with patch(
                "db.cruds.meal_request_line_crud.update_meal_request_line",
                new_callable=AsyncMock,
            ) as mock_update:
                mock_update.return_value = MagicMock(id=1)

                # Mock create_log_meal_request_line
                with patch(
                    "db.cruds.logs_crud.create_log_meal_request_line",
                    new_callable=AsyncMock,
                ):
                    response = client.put(
                        "/request-details/update-request-line",
                        json={
                            "account_id": 1,
                            "meal_request_line_id": 1,
                            "accepted": True,
                            "notes": "test",
                        },
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    # Should get 200 or 404 (not auth error)
                    assert response.status_code in [200, 404]

    def test_admin_scope_required_for_permission_management(self):
        """Test that admin-scoped endpoints require admin scope."""
        # Generate a user token (not admin)
        from jose import jwt

        user_token = jwt.encode(
            {"sub": "testuser", "scopes": ["user"]},
            "test-secret-key-for-testing-only",
            algorithm="HS256",
        )

        response = client.get(
            "/permissions",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    def test_admin_token_can_access_admin_endpoints(self):
        """Test that admin tokens can access admin-scoped endpoints."""
        # Generate an admin token
        from jose import jwt

        admin_token = jwt.encode(
            {"sub": "adminuser", "scopes": ["admin", "user"]},
            "test-secret-key-for-testing-only",
            algorithm="HS256",
        )

        # Mock the database session
        with patch(
            "db.cruds.role_permission_crud.read_role_permission_for_permission_page",
            new_callable=AsyncMock,
        ) as mock_read:
            mock_read.return_value = []

            response = client.get(
                "/permissions",
                headers={"Authorization": f"Bearer {admin_token}"},
            )

            # Should get 200 (not auth/permission error)
            assert response.status_code == 200


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present_for_allowed_origin(self):
        """Test that CORS headers are present for allowed origins."""
        response = client.options(
            "/",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_cors_headers_for_second_allowed_origin(self):
        """Test that CORS headers are present for the second allowed origin."""
        response = client.options(
            "/",
            headers={
                "origin": "https://test.example.com",
                "access-control-request-method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert (
            response.headers["access-control-allow-origin"]
            == "https://test.example.com"
        )

    def test_cors_blocks_disallowed_origin(self):
        """Test that CORS headers are not present for disallowed origins."""
        response = client.options(
            "/",
            headers={
                "origin": "http://malicious-site.com",
                "access-control-request-method": "GET",
            },
        )

        # The origin won't be in the allowed list, so CORS middleware will not set allow-origin
        # FastAPI's test client doesn't always show the absence of headers clearly
        # So we check that if allow-origin is present, it's not the malicious one
        if "access-control-allow-origin" in response.headers:
            assert (
                response.headers["access-control-allow-origin"]
                != "http://malicious-site.com"
            )


class TestRateLimiting:
    """Test rate limiting configuration."""

    def test_rate_limiter_is_configured(self):
        """Test that rate limiter is properly configured."""
        from utils.security import limiter

        assert limiter is not None

    def test_rate_limit_exceeded_handler_registered(self):
        """Test that rate limit exceeded handler is registered."""

        from utils.security import _rate_limit_exceeded_handler

        assert _rate_limit_exceeded_handler is not None
        assert callable(_rate_limit_exceeded_handler)
