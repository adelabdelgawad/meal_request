"""
Tests for application settings using pydantic-settings.

Tests the hierarchical Settings class from core.config with sub-settings:
  - settings.sec.*       (SecretSettings, env prefix SECRET_)
  - settings.api.*       (APISettings, env prefix API_)
  - settings.database.*  (DatabaseSettings, env prefix DATABASE_)
  - settings.ldap.*      (LDAPSettings, env prefix AD_)
  - settings.email.*     (EmailSettings, env prefix SMTP_)

Legacy env vars (MARIA_URL, JWT_SECRET_KEY, ALLOWED_ORIGINS, etc.)
are handled by model_post_init for backward compatibility.
"""

import os
from unittest.mock import patch


from core.config import Settings as AppSettings


class TestAppSettings:
    """Test suite for AppSettings configuration."""

    def test_env_loading_in_local_mode(self):
        """Test that legacy env vars are picked up via model_post_init."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "JWT_SECRET_KEY": "envtestkey",
                "LOG_LEVEL": "DEBUG",
            },
        ):
            settings = AppSettings()
            assert settings.environment == "local"
            # JWT_SECRET_KEY is a legacy env var handled by model_post_init
            assert settings.sec.jwt_secret_key == "envtestkey"
            assert settings.log_level == "DEBUG"

    def test_list_parsing_comma_separated(self):
        """Test parsing of ALLOWED_ORIGINS from comma-separated legacy env var."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "ALLOWED_ORIGINS": "http://a,http://b,http://c",
            },
        ):
            settings = AppSettings()
            assert settings.api.cors_origins == [
                "http://a",
                "http://b",
                "http://c",
            ]

    def test_list_parsing_prefixed_env_vars(self):
        """Test parsing of cors_origins from prefixed env var (JSON format)."""
        from core.config import APISettings

        with patch.dict(
            os.environ,
            {
                "API_CORS_ORIGINS": '["http://a","http://b","http://c"]',
            },
        ):
            api = APISettings(_env_file=None)
            assert api.cors_origins == [
                "http://a",
                "http://b",
                "http://c",
            ]

    def test_empty_origins_fallback(self):
        """Test that empty origins fallback to empty list."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
            },
        ):
            settings = AppSettings()
            # cors_origins should be an empty list when not set
            assert settings.api.cors_origins == []

    def test_jwt_secret_empty_in_local(self):
        """Test that jwt_secret_key is empty string by default in local mode."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
            },
        ):
            settings = AppSettings()
            assert settings.sec.jwt_secret_key == ""

    def test_required_fields_validation(self):
        """Test validation of required fields."""
        # Test that Settings can be created with minimal config
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
            },
        ):
            settings = AppSettings()
            assert settings.environment == "local"
            assert settings.sec.jwt_algorithm == "HS256"  # default value

    def test_vault_stub_activation_prod_mode(self):
        """Test that vault stub is called in production mode."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
            },
        ):
            # Mock the get_secret function in utils.secrets
            with patch("utils.secrets.get_secret") as mock_get_secret:
                mock_get_secret.return_value = "vault_secret_key"

                settings = AppSettings()
                # Should call get_secret for JWT_SECRET_KEY since it's empty
                mock_get_secret.assert_called_once_with("JWT_SECRET_KEY")
                assert settings.sec.jwt_secret_key == "vault_secret_key"

    def test_vault_stub_not_called_in_local(self):
        """Test that vault stub is not called in local mode."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "JWT_SECRET_KEY": "local_secret",
            },
        ):
            # Mock the get_secret function in utils.secrets
            with patch("utils.secrets.get_secret") as mock_get_secret:
                settings = AppSettings()
                # Should not call get_secret in local mode
                mock_get_secret.assert_not_called()
                assert settings.sec.jwt_secret_key == "local_secret"

    def test_vault_stub_raises_error(self):
        """Test behavior when vault stub raises an error."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
            },
        ):
            # Mock the get_secret function to raise an exception
            with patch("utils.secrets.get_secret") as mock_get_secret:
                mock_get_secret.side_effect = Exception("Vault not configured")

                # Should not raise error, just leave jwt_secret_key as empty
                settings = AppSettings()
                mock_get_secret.assert_called_once_with("JWT_SECRET_KEY")
                assert settings.sec.jwt_secret_key == ""

    def test_default_values(self):
        """Test default values for sub-settings (constructed without .env file)."""
        from core.config import (
            APISettings,
            DatabaseSettings,
            SecretSettings,
            LDAPSettings,
            EmailSettings,
        )

        # Construct sub-settings with _env_file=None to test pure defaults
        # without interference from the project's .env file
        api = APISettings(_env_file=None)
        db = DatabaseSettings(_env_file=None)
        sec = SecretSettings(_env_file=None)
        ldap = LDAPSettings(_env_file=None)
        email = EmailSettings(_env_file=None)

        assert sec.jwt_algorithm == "HS256"
        assert api.cors_origins == []
        assert db.url == ""
        assert db.hris_url == ""
        assert ldap.domain == ""
        assert ldap.server == ""
        assert ldap.service_account == ""
        assert ldap.service_password == ""
        assert email.primary_smtp_address == ""
        assert email.smtp_server == ""
        assert email.cc_recipient == ""

    def test_top_level_defaults(self):
        """Test default values for top-level Settings fields."""
        with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
            settings = AppSettings()
            assert settings.environment == "local"
            assert settings.log_level == "INFO"
            assert settings.enable_json_logs is False
            assert settings.log_file == ""

    def test_maria_url_parsing(self):
        """Test parsing of database URL from legacy APP_DB_URL env var."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "APP_DB_URL": "mysql+aiomysql://user:pass@localhost:3306/testdb?charset=utf8mb4",
            },
        ):
            settings = AppSettings()
            assert (
                settings.database.url
                == "mysql+aiomysql://user:pass@localhost:3306/testdb?charset=utf8mb4"
            )

    def test_settings_singleton(self):
        """Test that settings is a proper singleton."""
        from core.config import settings as global_settings

        AppSettings()
        # Note: Each instantiation creates a new instance, but the global settings instance is what we use
        assert isinstance(global_settings, AppSettings)

    def test_get_secret_fallback(self):
        """Test the model_post_init logic for secret loading."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
            },
        ):
            # Mock get_secret to return a value
            with patch("utils.secrets.get_secret") as mock_get_secret:
                mock_get_secret.return_value = "vault_secret"

                settings = AppSettings()
                mock_get_secret.assert_called_once_with("JWT_SECRET_KEY")
                assert settings.sec.jwt_secret_key == "vault_secret"

    def test_multiple_origins_format(self):
        """Test various ALLOWED_ORIGINS formats via legacy env var."""
        # Test with spaces
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "ALLOWED_ORIGINS": " http://a , http://b ",
            },
        ):
            settings = AppSettings()
            assert settings.api.cors_origins == ["http://a", "http://b"]
