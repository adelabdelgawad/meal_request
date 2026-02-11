"""
Tests for token functionality including issuance, refresh, and revocation.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db.cruds.tokens_crud_async import TokenCRUDAsync
from db.model import RevokedToken
from routers.sec_login import router as login_router
from utils.logging_config import setup_logging
from utils.security import create_jwt, decode_jwt

# Setup logging for tests
setup_logging(log_level="DEBUG", enable_json_logs=False)


class TestTokenCRUD:
    """Test token CRUD operations."""

    def test_create_revoked_token(self):
        """Test creating a revoked token."""
        # Create mock session
        mock_session = Mock(spec=Session)

        # Test data
        jti = "test-jti-123"
        token_type = "refresh"
        account_id = 1
        expires_at = datetime.now() + timedelta(days=30)

        # Call create method
        result = TokenCRUDAsync.create_revoked_token(
            db=mock_session,
            jti=jti,
            token_type=token_type,
            account_id=account_id,
            expires_at=expires_at,
        )

        # Verify
        assert isinstance(result, RevokedToken)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

        # Check the added object
        added_obj = mock_session.add.call_args[0][0]
        assert added_obj.jti == jti
        assert added_obj.token_type == token_type
        assert added_obj.account_id == account_id

    def test_get_revoked_token_by_jti(self):
        """Test getting a revoked token by JTI."""
        # Create mock session
        mock_session = Mock(spec=Session)

        # Setup mock query result
        mock_token = RevokedToken(
            jti="test-jti-123", token_type="refresh", account_id=1
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            mock_token
        )

        # Call get method
        result = TokenCRUDAsync.get_revoked_token_by_jti(
            db=mock_session, jti="test-jti-123"
        )

        # Verify
        assert result == mock_token
        mock_session.execute.assert_called_once()

    def test_is_token_revoked(self):
        """Test checking if a token is revoked."""
        # Create mock session
        mock_session = Mock(spec=Session)

        # Test with revoked token
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            RevokedToken()
        )
        assert (
            TokenCRUDAsync.is_token_revoked(mock_session, "revoked-jti")
            is True
        )

        # Test with non-revoked token
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            None
        )
        assert (
            TokenCRUDAsync.is_token_revoked(mock_session, "valid-jti") is False
        )

    def test_revoke_token_existing(self):
        """Test revoking a token that is already revoked."""
        # Create mock session
        mock_session = Mock(spec=Session)

        # Setup mock query to return existing token
        mock_session.execute.return_value.scalars.return_value.first.return_value = RevokedToken(
            jti="existing-jti"
        )

        # Call revoke method
        result = TokenCRUDAsync.revoke_token(
            db=mock_session,
            jti="existing-jti",
            token_type="refresh",
            account_id=1,
            expires_at=datetime.now() + timedelta(days=30),
        )

        # Verify - should return existing token without creating new one
        assert isinstance(result, RevokedToken)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_revoke_token_new(self):
        """Test revoking a new token."""
        # Create mock session
        mock_session = Mock(spec=Session)

        # Setup mock query to return None (not revoked)
        mock_session.execute.return_value.scalars.return_value.first.return_value = (
            None
        )
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()

        # Call revoke method
        result = TokenCRUDAsync.revoke_token(
            db=mock_session,
            jti="new-jti",
            token_type="refresh",
            account_id=1,
            expires_at=datetime.now() + timedelta(days=30),
        )

        # Verify - should create new revoked token
        assert isinstance(result, RevokedToken)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestJWTFunctions:
    """Test JWT creation and decoding functions."""

    def test_create_jwt_access_token(self):
        """Test creating an access token."""
        data = {
            "sub": "testuser",
            "account_id": 1,
            "scopes": ["user"],
            "roles": ["user"],
        }
        expires_delta = timedelta(minutes=15)

        # Create token
        token, jti = create_jwt(data, "access", expires_delta)

        # Verify token was created
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT should have 3 parts

        # Verify JTI was generated
        assert jti is not None
        assert isinstance(jti, str)

    def test_create_jwt_refresh_token(self):
        """Test creating a refresh token."""
        data = {
            "sub": "testuser",
            "account_id": 1,
            "scopes": ["user"],
            "roles": ["user"],
        }
        expires_delta = timedelta(days=30)

        # Create token
        token, jti = create_jwt(data, "refresh", expires_delta)

        # Verify token was created
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

        # Verify JTI was generated
        assert jti is not None
        assert isinstance(jti, str)

    def test_decode_jwt_valid_token(self):
        """Test decoding a valid token."""
        data = {"sub": "testuser", "account_id": 1}
        expires_delta = timedelta(minutes=15)

        # Create and decode token
        token, _ = create_jwt(data, "access", expires_delta)
        decoded = decode_jwt(token)

        # Verify decoded data
        assert decoded["sub"] == "testuser"
        assert decoded["account_id"] == 1
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "jti" in decoded

    def test_decode_jwt_invalid_token(self):
        """Test decoding an invalid token."""
        # Test with malformed token
        with pytest.raises(Exception):  # FastAPI HTTPException
            decode_jwt("invalid.token.here")

        # Test with completely invalid token
        with pytest.raises(Exception):  # FastAPI HTTPException
            decode_jwt("not.a.jwt.token")


class TestTokenEndpoints:
    """Test token-related API endpoints."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()
        app.include_router(login_router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @patch("routers.sec_login.Login")
    def test_login_issue_tokens(self, mock_login_class, client):
        """Test login endpoint issues both access and refresh tokens."""
        # Setup mock account
        mock_account = Mock()
        mock_account.id = 1
        mock_account.username = "testuser"
        mock_account.is_super_admin = False

        # Setup mock login
        mock_login = Mock()
        mock_login.is_authenticated = True
        mock_login.account = mock_account
        mock_login_class.return_value = mock_login

        # Mock page permissions
        with patch(
            "routers.sec_login.read_pages_by_account", new_callable=AsyncMock
        ) as mock_read_pages:
            mock_read_pages.return_value = []

            # Make request
            response = client.post(
                "/login", json={"username": "testuser", "password": "testpass"}
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert "token_type" in data
            assert "expires_in" in data
            assert "account" in data
            assert data["token_type"] == "bearer"

            # Verify access token structure
            access_token = data["access_token"]
            decoded = decode_jwt(access_token)
            assert decoded["type"] == "access"
            assert decoded["sub"] == "testuser"
            assert decoded["account_id"] == 1

            # Verify refresh token structure
            refresh_token = data["refresh_token"]
            decoded = decode_jwt(refresh_token)
            assert decoded["type"] == "refresh"
            assert decoded["sub"] == "testuser"
            assert decoded["account_id"] == 1

    def test_logout_revokes_token(self, client):
        """Test logout endpoint revokes a token."""
        # Create a test token
        data = {"sub": "testuser", "account_id": 1}
        expires_delta = timedelta(minutes=15)
        token, _ = create_jwt(data, "access", expires_delta)

        # Mock database session
        with patch("routers.sec_login.TokenCRUDAsync") as mock_token_crud:
            mock_token_crud.revoke_token.return_value = Mock()

            # Make request
            response = client.post("/logout", json={"token": token})

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "revoked" in data["message"].lower()

            # Verify revoke_token was called
            mock_token_crud.revoke_token.assert_called_once()


class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        app = FastAPI()
        app.include_router(login_router)
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)

    @patch("routers.sec_login.decode_jwt")
    @patch("routers.sec_login.TokenCRUDAsync")
    def test_refresh_token_valid(self, mock_token_crud, mock_decode, client):
        """Test refreshing a valid token."""
        # Setup mock decoded token
        mock_decode.return_value = {
            "sub": "testuser",
            "account_id": 1,
            "type": "refresh",
            "jti": "refresh-jti-123",
            "scopes": ["user"],
            "roles": ["user"],
        }

        # Setup mock token not revoked
        mock_token_crud.is_token_revoked.return_value = False

        # Setup mock account
        with patch(
            "routers.sec_login.get_account_by_id", new_callable=AsyncMock
        ) as mock_get_account:
            mock_account = Mock()
            mock_account.id = 1
            mock_account.username = "testuser"
            mock_get_account.return_value = mock_account

            # Create refresh token
            refresh_data = {"sub": "testuser", "account_id": 1}
            expires_delta = timedelta(days=30)
            refresh_token, _ = create_jwt(
                refresh_data, "refresh", expires_delta
            )

            # Make request
            response = client.post(
                "/refresh", json={"refresh_token": refresh_token}
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert "expires_in" in data
            assert data["token_type"] == "bearer"

            # Verify new access token
            access_token = data["access_token"]
            decoded = decode_jwt(access_token)
            assert decoded["type"] == "access"
            assert decoded["sub"] == "testuser"
            assert decoded["account_id"] == 1

    @patch("routers.sec_login.decode_jwt")
    def test_refresh_token_invalid_type(self, mock_decode, client):
        """Test refresh endpoint rejects non-refresh tokens."""
        # Setup mock decoded token with wrong type
        mock_decode.return_value = {
            "sub": "testuser",
            "type": "access",  # Wrong type!
        }

        # Make request
        refresh_data = {"sub": "testuser", "account_id": 1}
        expires_delta = timedelta(minutes=15)
        access_token, _ = create_jwt(refresh_data, "access", expires_delta)

        response = client.post(
            "/refresh", json={"refresh_token": access_token}
        )

        # Verify response
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])
