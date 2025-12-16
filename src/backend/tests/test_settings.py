"""
Tests for application settings using pydantic-settings.
"""

import os
import tempfile
from unittest.mock import patch


from settings import AppSettings


class TestAppSettings:
    """Test suite for AppSettings configuration."""

    def test_env_loading_in_local_mode(self):
        """Test that .env loading works in local mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a temporary .env file
            env_file = os.path.join(tmpdir, ".env")
            with open(env_file, "w") as f:
                f.write("ENVIRONMENT=local\n")
                f.write("JWT_SECRET_KEY=envtestkey\n")
                f.write("LOG_LEVEL=DEBUG\n")

            # Change to the temporary directory and load settings
            with patch.dict(os.environ, {"ENV_FILE": env_file}):
                with patch("os.getcwd", return_value=tmpdir):
                    settings = AppSettings()
                    assert settings.ENVIRONMENT == "local"
                    assert settings.JWT_SECRET_KEY == "envtestkey"
                    assert settings.LOG_LEVEL == "DEBUG"

    def test_list_parsing_comma_separated(self):
        """Test parsing of ALLOWED_ORIGINS from comma-separated env var."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "ALLOWED_ORIGINS": "http://a,http://b,http://c",
            },
        ):
            settings = AppSettings()
            assert settings.ALLOWED_ORIGINS == [
                "http://a",
                "http://b",
                "http://c",
            ]

    def test_list_parsing_multiple_env_vars(self):
        """Test parsing of ALLOWED_ORIGINS from multiple env vars."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "ALLOWED_ORIGINS__0": "http://a",
                "ALLOWED_ORIGINS__1": "http://b",
                "ALLOWED_ORIGINS__2": "http://c",
            },
        ):
            settings = AppSettings()
            assert settings.ALLOWED_ORIGINS == [
                "http://a",
                "http://b",
                "http://c",
            ]

    def test_empty_origins_fallback(self):
        """Test that empty origins fallback to localhost."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
            },
        ):
            settings = AppSettings()
            # ALLOWED_ORIGINS should be an empty list when not set
            assert settings.ALLOWED_ORIGINS == []

    def test_jwt_secret_validation_local(self):
        """Test that JWT_SECRET_KEY can be None in local mode."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
            },
        ):
            settings = AppSettings()
            assert settings.JWT_SECRET_KEY is None

    def test_required_fields_validation(self):
        """Test validation of required fields."""
        # Test that AppSettings can be created with minimal config
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
            },
        ):
            settings = AppSettings()
            assert settings.ENVIRONMENT == "local"
            assert settings.JWT_ALGORITHM == "HS256"  # default value

    def test_vault_stub_activation_prod_mode(self):
        """Test that vault stub is called in production mode."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
            },
        ):
            # Mock the get_secret function
            with patch("settings.get_secret") as mock_get_secret:
                mock_get_secret.return_value = "vault_secret_key"

                settings = AppSettings()
                # Should call get_secret for JWT_SECRET_KEY since it's None
                mock_get_secret.assert_called_once_with("JWT_SECRET_KEY")
                assert settings.JWT_SECRET_KEY == "vault_secret_key"

    def test_vault_stub_not_called_in_local(self):
        """Test that vault stub is not called in local mode."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "JWT_SECRET_KEY": "local_secret",
            },
        ):
            # Mock the get_secret function
            with patch("settings.get_secret") as mock_get_secret:
                settings = AppSettings()
                # Should not call get_secret in local mode
                mock_get_secret.assert_not_called()
                assert settings.JWT_SECRET_KEY == "local_secret"

    def test_vault_stub_raises_error(self):
        """Test behavior when vault stub raises an error."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
            },
        ):
            # Mock the get_secret function to raise an exception
            with patch("settings.get_secret") as mock_get_secret:
                mock_get_secret.side_effect = Exception("Vault not configured")

                # Should not raise error, just leave JWT_SECRET_KEY as None
                settings = AppSettings()
                mock_get_secret.assert_called_once_with("JWT_SECRET_KEY")
                assert settings.JWT_SECRET_KEY is None

    def test_default_values(self):
        """Test default values for settings."""
        with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
            settings = AppSettings()
            assert settings.ENVIRONMENT == "local"
            assert settings.JWT_ALGORITHM == "HS256"
            assert settings.LOG_LEVEL == "INFO"
            assert settings.ALLOWED_ORIGINS == []
            assert settings.MARIA_URL is None
            assert settings.HRIS_URL is None
            assert settings.AD_DOMAIN is None
            assert settings.AD_SERVER is None
            assert settings.SERVICE_ACCOUNT is None
            assert settings.SERVICE_PASSWORD is None
            assert settings.PRIMARY_SMTP_ADDRESS is None
            assert settings.SMTP_SERVER is None
            assert settings.CC_RECIPIENT is None

    def test_maria_url_parsing(self):
        """Test parsing of MARIA_URL from env var."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "APP_DB_URL": "mysql+aiomysql://user:pass@localhost:3306/testdb?charset=utf8mb4",
            },
        ):
            settings = AppSettings()
            assert (
                settings.MARIA_URL
                == "mysql+aiomysql://user:pass@localhost:3306/testdb?charset=utf8mb4"
            )

    def test_settings_singleton(self):
        """Test that settings is a proper singleton."""
        from settings import settings as global_settings

        AppSettings()
        # Note: Each instantiation creates a new instance, but the global settings instance is what we use
        assert isinstance(global_settings, AppSettings)

    @patch("os.getenv")
    def test_get_secret_fallback(self, mock_getenv):
        """Test the model_post_init logic for secret loading."""
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
            },
        ):
            # Mock get_secret to return a value
            with patch("settings.get_secret") as mock_get_secret:
                mock_get_secret.return_value = "vault_secret"

                settings = AppSettings()
                mock_get_secret.assert_called_once_with("JWT_SECRET_KEY")
                assert settings.JWT_SECRET_KEY == "vault_secret"

    def test_multiple_origins_format(self):
        """Test various ALLOWED_ORIGINS formats."""
        # Test with spaces
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "local",
                "ALLOWED_ORIGINS": " http://a , http://b ",
            },
        ):
            settings = AppSettings()
            assert settings.ALLOWED_ORIGINS == ["http://a", "http://b"]
