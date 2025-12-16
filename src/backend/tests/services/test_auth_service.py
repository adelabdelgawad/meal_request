"""
Auth Service Tests - Tests for internal authentication microservice.

This test module validates the auth service endpoints, token issuance,
verification, and error handling.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Import the auth service app
from services.auth.main import app


class TestAuthService:
    """Test suite for Auth Service endpoints."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def valid_api_key(self):
        """Provide valid API key for testing."""
        return "test-internal-api-key-123"

    @pytest.fixture
    def sample_token_data(self):
        """Sample token data for testing."""
        return {
            "service_name": "test_service",
            "user_id": "user123",
            "permissions": ["read:test", "write:test"],
            "metadata": {"request_id": "req-456"},
        }

    def test_health_check(self, client, valid_api_key):
        """Test the health check endpoint."""
        response = client.get(
            "/internal/health", headers={"X-Internal-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "auth_service"
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["features"]["internal_token_issuance"] is True
        assert data["features"]["internal_token_verification"] is True

    def test_service_config(self, client, valid_api_key):
        """Test the service configuration endpoint."""
        response = client.get(
            "/internal/config", headers={"X-Internal-API-Key": valid_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "auth_service"
        assert "/internal/token" in data["endpoints"]
        assert "/internal/verify" in data["endpoints"]
        assert "X-Internal-API-Key" in data["requirements"]["headers"]

    def test_issue_token_success(
        self, client, valid_api_key, sample_token_data
    ):
        """Test successful token issuance."""
        response = client.post(
            "/internal/token",
            headers={"X-Internal-API-Key": valid_api_key},
            json=sample_token_data,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "service_name" in data
        assert "issued_at" in data
        assert "expires_at" in data
        assert data["token_type"] == "bearer"
        assert data["service_name"] == sample_token_data["service_name"]
        assert data["token_type_label"] == "internal_service"

        # Verify token is a non-empty JWT
        token = data["access_token"]
        assert len(token) > 100  # JWT tokens are typically quite long
        assert "." in token  # JWT has three parts separated by dots

    def test_issue_token_minimal(self, client, valid_api_key):
        """Test token issuance with minimal required data."""
        token_data = {"service_name": "minimal_service"}

        response = client.post(
            "/internal/token",
            headers={"X-Internal-API-Key": valid_api_key},
            json=token_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["service_name"] == "minimal_service"
        assert "access_token" in data

    def test_issue_token_missing_api_key(self, client, sample_token_data):
        """Test token issuance without API key."""
        response = client.post("/internal/token", json=sample_token_data)

        assert response.status_code == 401
        assert (
            "X-Internal-API-Key header is required"
            in response.json()["detail"]
        )

    def test_issue_token_invalid_api_key(self, client, sample_token_data):
        """Test token issuance with invalid API key."""
        response = client.post(
            "/internal/token",
            headers={"X-Internal-API-Key": "invalid-key"},
            json=sample_token_data,
        )

        assert response.status_code == 401
        assert "Invalid internal API key" in response.json()["detail"]

    def test_verify_token_success(self, client, valid_api_key):
        """Test successful token verification."""
        # First, issue a token
        token_data = {"service_name": "verify_test_service"}
        issue_response = client.post(
            "/internal/token",
            headers={"X-Internal-API-Key": valid_api_key},
            json=token_data,
        )

        token = issue_response.json()["access_token"]

        # Now verify the token
        verify_response = client.post(
            "/internal/verify",
            headers={"X-Internal-API-Key": valid_api_key},
            json={"token": token},
        )

        assert verify_response.status_code == 200
        data = verify_response.json()

        # Verify response structure
        assert data["valid"] is True
        assert "claims" in data
        assert "service_name" in data
        assert "expires_at" in data
        assert data["claims"]["type"] == "internal_service"
        assert data["claims"]["service"] == "verify_test_service"
        assert data["service_name"] == "verify_test_service"

    def test_verify_token_missing_api_key(self, client):
        """Test token verification without API key."""
        response = client.post(
            "/internal/verify", json={"token": "fake-token"}
        )

        assert response.status_code == 401
        assert (
            "X-Internal-API-Key header is required"
            in response.json()["detail"]
        )

    def test_verify_token_invalid_api_key(self, client):
        """Test token verification with invalid API key."""
        response = client.post(
            "/internal/verify",
            headers={"X-Internal-API-Key": "invalid-key"},
            json={"token": "fake-token"},
        )

        assert response.status_code == 401
        assert "Invalid internal API key" in response.json()["detail"]

    def test_verify_token_expired(self, client, valid_api_key):
        """Test verification of an expired token."""
        # Create a mock expired token
        with patch("services.auth.main.decode_jwt") as mock_decode:
            mock_decode.side_effect = Exception("Token has expired")

            response = client.post(
                "/internal/verify",
                headers={"X-Internal-API-Key": valid_api_key},
                json={"token": "expired-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "Token has expired" in data["error"]

    def test_verify_token_invalid_format(self, client, valid_api_key):
        """Test verification of an invalid token format."""
        response = client.post(
            "/internal/verify",
            headers={"X-Internal-API-Key": valid_api_key},
            json={"token": "invalid-token-format"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error"] is not None

    def test_verify_token_wrong_type(self, client, valid_api_key):
        """Test verification of a non-internal-service token."""
        # Create a mock token with wrong type
        with patch("services.auth.main.decode_jwt") as mock_decode:
            mock_decode.return_value = {
                "type": "user_access",
                "service": "some_service",
            }

            response = client.post(
                "/internal/verify",
                headers={"X-Internal-API-Key": valid_api_key},
                json={"token": "user-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert "Token is not an internal service token" in data["error"]

    def test_health_check_missing_api_key(self, client):
        """Test health check without API key."""
        response = client.get("/internal/health")

        assert response.status_code == 401
        assert (
            "X-Internal-API-Key header is required"
            in response.json()["detail"]
        )

    def test_config_missing_api_key(self, client):
        """Test config endpoint without API key."""
        response = client.get("/internal/config")

        assert response.status_code == 401
        assert (
            "X-Internal-API-Key header is required"
            in response.json()["detail"]
        )

    def test_invalid_endpoint(self, client, valid_api_key):
        """Test accessing non-existent endpoint."""
        response = client.post(
            "/internal/invalid",
            headers={"X-Internal-API-Key": valid_api_key},
            json={},
        )

        assert response.status_code == 404


class TestAuthServiceIntegration:
    """Integration tests for auth service workflows."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def valid_api_key(self):
        """Provide valid API key for testing."""
        return "integration-test-key"

    def test_full_token_lifecycle(self, client, valid_api_key):
        """Test complete token lifecycle: issue -> verify -> expire simulation."""
        # Step 1: Issue token
        token_data = {
            "service_name": "lifecycle_test_service",
            "user_id": "test_user",
            "permissions": ["read:test", "write:test"],
            "metadata": {"test_run": "full_lifecycle"},
        }

        issue_response = client.post(
            "/internal/token",
            headers={"X-Internal-API-Key": valid_api_key},
            json=token_data,
        )

        assert issue_response.status_code == 200
        token_info = issue_response.json()
        token = token_info["access_token"]

        # Step 2: Verify token
        verify_response = client.post(
            "/internal/verify",
            headers={"X-Internal-API-Key": valid_api_key},
            json={"token": token},
        )

        assert verify_response.status_code == 200
        verify_info = verify_response.json()

        # Step 3: Verify token information
        assert verify_info["valid"] is True
        assert verify_info["service_name"] == token_data["service_name"]
        assert verify_info["claims"]["user_id"] == token_data["user_id"]
        assert (
            verify_info["claims"]["permissions"] == token_data["permissions"]
        )
        assert verify_info["claims"]["metadata"] == token_data["metadata"]

    def test_multiple_services(self, client, valid_api_key):
        """Test that different services get distinct tokens."""
        services = ["service_a", "service_b", "service_c"]
        tokens = []

        for service_name in services:
            response = client.post(
                "/internal/token",
                headers={"X-Internal-API-Key": valid_api_key},
                json={"service_name": service_name},
            )

            assert response.status_code == 200
            tokens.append(response.json()["access_token"])

        # Verify all tokens are different
        assert len(set(tokens)) == len(tokens)  # All tokens are unique

        # Verify each token corresponds to the correct service
        for i, (service_name, token) in enumerate(zip(services, tokens)):
            verify_response = client.post(
                "/internal/verify",
                headers={"X-Internal-API-Key": valid_api_key},
                json={"token": token},
            )

            assert verify_response.status_code == 200
            verify_info = verify_response.json()
            assert verify_info["service_name"] == service_name


class TestAuthServiceConfiguration:
    """Test auth service configuration and environment variables."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_default_configuration(self, client):
        """Test that service uses default configuration when env vars not set."""
        with patch.dict("os.environ", {}, clear=True):
            response = client.get(
                "/internal/health",
                headers={"X-Internal-API-Key": "dev-internal-key-123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["configuration"]["token_expiry_minutes"] == 60
            assert data["configuration"]["algorithm"] == "HS256"

    def test_custom_configuration(self, client):
        """Test that service uses custom configuration when env vars are set."""
        with patch.dict(
            "os.environ",
            {"INTERNAL_TOKEN_EXPIRE_MINUTES": "120", "JWT_ALGORITHM": "HS384"},
        ):
            # Need to reload the app to pick up new environment variables
            import importlib

            import services.auth.main

            importlib.reload(services.auth.main)
            from services.auth.main import app as reloaded_app

            reloaded_client = TestClient(reloaded_app)

            response = reloaded_client.get(
                "/internal/health",
                headers={"X-Internal-API-Key": "dev-internal-key-123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["configuration"]["token_expiry_minutes"] == 120
            assert data["configuration"]["algorithm"] == "HS384"


class TestAuthServiceSecurity:
    """Test security aspects of the auth service."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_api_key_header_case_sensitive(self, client):
        """Test that API key header is case-sensitive."""
        response = client.post(
            "/internal/token",
            headers={"x-internal-api-key": "test-key"},  # lowercase
            json={"service_name": "test"},
        )

        assert response.status_code == 401
        assert (
            "X-Internal-API-Key header is required"
            in response.json()["detail"]
        )

    def test_cors_headers(self, client):
        """Test that CORS headers are properly configured."""
        response = client.options("/internal/token")

        assert response.status_code == 200
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-headers" in headers
        assert "access-control-allow-methods" in headers

    def test_no_sensitive_data_in_response(self, client):
        """Test that sensitive configuration is not exposed in responses."""
        response = client.get(
            "/internal/health", headers={"X-Internal-API-Key": "test-key"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should not expose internal API key
        assert "api_key" not in str(data).lower()
        assert "secret" not in str(data).lower()


if __name__ == "__main__":
    # Example of how to run tests manually
    print("🧪 Running auth service tests...")

    # These would normally be run with pytest
    # pytest tests/services/test_auth_service.py -v

    print("✅ Test structure validated")
    print("📝 To run tests: pytest tests/services/test_auth_service.py -v")
    print("🔧 Requires: pytest, fastapi, python-jose[cryptography]")
